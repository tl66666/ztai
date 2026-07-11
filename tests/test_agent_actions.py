import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import app as app_module

from utils.domain.database import APPLICATION_STATUSES, connect, migrate_database


class AgentActionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "actions.db")
        migrate_database(self.db_path)
        from utils.agent_runtime.actions import ActionProposalError, ActionProposalService

        self.error_type = ActionProposalError
        self.service = ActionProposalService(self.db_path, local_user_id=1)
        with connect(self.db_path) as conn:
            self.resume_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Base', 'private resume body')"
            ).lastrowid

    def tearDown(self):
        self.temp_dir.cleanup()

    def propose(self, action_type, arguments, **kwargs):
        return self.service.propose(1, action_type, arguments, **kwargs)

    def test_create_preview_normalizes_and_redacts_sensitive_content(self):
        proposal = self.propose(
            "create_opportunity",
            {
                "company": "  Acme  ",
                "job_title": " Engineer ",
                "jd_text": "SECRET-JD " * 20,
                "contact_info": "secret@example.com",
            },
            rationale="  useful next step  ",
        )

        self.assertEqual(proposal["arguments"]["company"], "Acme")
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(proposal["risk_level"], "medium")
        self.assertEqual(proposal["rationale"], "useful next step")
        serialized = json.dumps(proposal, ensure_ascii=False)
        self.assertNotIn("SECRET-JD", proposal["preview"])
        self.assertNotIn("secret@example.com", proposal["preview"])
        self.assertIn("Acme", proposal["preview"])
        self.assertIn("SECRET-JD", serialized)

    def test_rejects_invalid_action_arguments_and_foreign_targets(self):
        with self.assertRaisesRegex(ValueError, "action type"):
            self.propose("delete_opportunity", {"opportunity_id": 1})
        with self.assertRaisesRegex(ValueError, "company"):
            self.propose("create_opportunity", {"job_title": "Engineer"})
        with self.assertRaisesRegex(ValueError, "object"):
            self.service.propose(1, "create_opportunity", [])

        with connect(self.db_path) as conn:
            foreign_id = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (2, 'Other', 'Role')"
            ).lastrowid
        with self.assertRaisesRegex(LookupError, "opportunity"):
            self.propose(
                "update_opportunity",
                {"opportunity_id": foreign_id, "changes": {"notes": "no"}},
            )

    def test_rejects_invalid_nested_values_before_persisting(self):
        invalid_cases = [
            ("create_action_item", {"title": "Task", "status": "invented"}),
            (
                "create_resume_version",
                {
                    "resume_id": self.resume_id,
                    "content": "content",
                    "metadata": {"source_type": "external"},
                },
            ),
            (
                "save_career_report",
                {"report_type": "weekly", "content": {}, "status": "published"},
            ),
            ("set_career_goal", {"cities": "Shanghai"}),
        ]
        for action_type, arguments in invalid_cases:
            with self.subTest(action_type=action_type), self.assertRaises(ValueError):
                self.propose(action_type, arguments)

        opportunity = self.service.confirm(
            1,
            self.propose(
                "create_opportunity",
                {"company": "Acme", "job_title": "Engineer", "status": "Offer"},
            )["id"],
        )["result"]
        with self.assertRaisesRegex(ValueError, "transition"):
            self.propose(
                "update_opportunity",
                {
                    "opportunity_id": opportunity["id"],
                    "changes": {"status": APPLICATION_STATUSES[0]},
                },
            )

        with connect(self.db_path) as conn:
            invalid_count = conn.execute(
                "SELECT COUNT(*) FROM agent_action_proposals WHERE status = 'pending'"
            ).fetchone()[0]
        self.assertEqual(invalid_count, 0)

    def test_every_public_method_enforces_local_user(self):
        proposal = self.propose(
            "create_opportunity", {"company": "Acme", "job_title": "Engineer"}
        )
        calls = [
            lambda: self.service.propose(2, "create_opportunity", {}),
            lambda: self.service.get(2, proposal["id"]),
            lambda: self.service.edit(2, proposal["id"], {}),
            lambda: self.service.confirm(2, proposal["id"]),
            lambda: self.service.cancel(2, proposal["id"]),
            lambda: self.service.list_pending(2),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(PermissionError):
                call()

    def test_edit_only_allows_action_specific_safe_fields(self):
        proposal = self.propose(
            "create_opportunity", {"company": "Acme", "job_title": "Engineer"}
        )
        edited = self.service.edit(
            1, proposal["id"], {"company": "Better", "notes": "Follow up"}
        )
        self.assertEqual(edited["arguments"]["company"], "Better")
        self.assertIn("Better", edited["preview"])

        for changes in (
            {"action_type": "create_action_item"},
            {"user_id": 2},
            {"idempotency_key": "forged"},
            {"unknown": "value"},
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "edit"):
                self.service.edit(1, proposal["id"], changes)

    def test_confirm_maps_every_allowed_action_through_career_service(self):
        opportunity = self.service.confirm(
            1,
            self.propose(
                "create_opportunity", {"company": "Acme", "job_title": "Engineer"}
            )["id"],
        )["result"]
        opportunity_id = opportunity["id"]

        cases = [
            ("set_career_goal", {"target_role": "Staff Engineer"}, "career_profile"),
            (
                "create_resume_version",
                {
                    "resume_id": self.resume_id,
                    "content": "tailored private content",
                    "metadata": {"version_label": "Acme", "source_type": "agent"},
                },
                "resume",
            ),
            (
                "link_opportunity_resume",
                {"opportunity_id": opportunity_id, "resume_id": self.resume_id},
                "opportunity",
            ),
            (
                "create_interview_plan",
                {"opportunity_id": opportunity_id, "title": "Prepare interview"},
                "action_item",
            ),
            ("create_action_item", {"title": "Research team"}, "action_item"),
            (
                "update_opportunity",
                {"opportunity_id": opportunity_id, "changes": {"notes": "Called"}},
                "opportunity",
            ),
            (
                "save_career_report",
                {
                    "report_type": "weekly",
                    "title": "Week 1",
                    "content": {"summary": "Progress"},
                },
                "career_report",
            ),
        ]
        created_action_id = None
        for action_type, arguments, entity_type in cases:
            with self.subTest(action_type=action_type):
                completed = self.service.confirm(
                    1, self.propose(action_type, arguments)["id"]
                )
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(completed["result"]["entity_type"], entity_type)
                if action_type == "create_action_item":
                    created_action_id = completed["result"]["id"]

        completed = self.service.confirm(
            1,
            self.propose(
                "complete_action_item",
                {"action_id": created_action_id, "evidence": "done"},
            )["id"],
        )
        self.assertEqual(completed["result"]["status"], "completed")

        with connect(self.db_path) as conn:
            event_types = {
                row[0] for row in conn.execute("SELECT event_type FROM domain_events")
            }
        self.assertTrue(
            {
                "profile.updated",
                "opportunity.created",
                "resume.version_created",
                "opportunity.updated",
                "action_item.created",
                "action_item.completed",
                "career_report.saved",
            }.issubset(event_types)
        )

    def test_cancel_expiry_and_invalid_states_are_stable(self):
        proposal = self.propose(
            "create_action_item", {"title": "Later"}
        )
        cancelled = self.service.cancel(1, proposal["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        with self.assertRaises(self.error_type) as cancelled_error:
            self.service.confirm(1, proposal["id"])
        self.assertEqual(cancelled_error.exception.code, "proposal_cancelled")

        expiring = self.propose("create_action_item", {"title": "Expired"})
        expired_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agent_action_proposals SET expires_at = ? WHERE id = ?",
                (expired_at, expiring["id"]),
            )
        self.assertEqual(self.service.get(1, expiring["id"])["status"], "expired")
        self.assertIsNotNone(self.service.get(1, expiring["id"])["expired_at"])
        self.assertEqual(self.service.list_pending(1), [])
        with self.assertRaises(self.error_type) as expired_error:
            self.service.confirm(1, expiring["id"])
        self.assertEqual(expired_error.exception.code, "proposal_expired")

    def test_completed_confirm_is_idempotent_sequentially_and_concurrently(self):
        proposal = self.propose(
            "create_action_item", {"title": "Exactly once"}
        )
        first = self.service.confirm(1, proposal["id"])
        second = self.service.confirm(1, proposal["id"])
        self.assertEqual(first["result"], second["result"])

        concurrent = self.propose(
            "create_action_item", {"title": "Concurrent once"}
        )
        results = []
        errors = []
        barrier = threading.Barrier(2)

        def confirm():
            try:
                barrier.wait()
                results.append(self.service.confirm(1, concurrent["id"])["result"])
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=confirm) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(results[0], results[1])
        with connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE title = 'Concurrent once'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_executor_failure_marks_failed_without_false_completion(self):
        proposal = self.propose(
            "create_action_item", {"title": "Will fail"}
        )
        with patch.object(
            self.service.career_service,
            "create_action_item",
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaises(self.error_type) as raised:
                self.service.confirm(1, proposal["id"])
        self.assertEqual(raised.exception.code, "execution_failed")
        failed = self.service.get(1, proposal["id"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_code"], "execution_failed")
        self.assertIsNone(failed["result"])


class AgentActionAPITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = app_module.DB_PATH
        app_module.DB_PATH = os.path.join(self.temp_dir.name, "api-actions.db")
        app_module._agent_action_service = None
        app_module.init_db()
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        self.service = app_module.get_agent_action_service()

    def tearDown(self):
        app_module._agent_action_service = None
        app_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_api_lists_gets_edits_confirms_and_cancels(self):
        editable = self.service.propose(1, "create_action_item", {"title": "Draft"})
        pending = self.client.get("/api/agent/actions?status=pending")
        fetched = self.client.get(f"/api/agent/actions/{editable['id']}")
        edited = self.client.post(
            f"/api/agent/actions/{editable['id']}/edit", json={"title": "Final"}
        )
        confirmed = self.client.post(
            f"/api/agent/actions/{editable['id']}/confirm", json={}
        )
        cancellable = self.service.propose(1, "create_action_item", {"title": "Cancel"})
        cancelled = self.client.post(
            f"/api/agent/actions/{cancellable['id']}/cancel", json={}
        )

        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.get_json()["actions"][0]["id"], editable["id"])
        self.assertEqual(fetched.get_json()["action"]["id"], editable["id"])
        self.assertEqual(edited.get_json()["action"]["arguments"]["title"], "Final")
        self.assertEqual(confirmed.get_json()["action"]["status"], "completed")
        self.assertEqual(cancelled.get_json()["action"]["status"], "cancelled")

    def test_api_returns_stable_json_errors_for_input_ownership_and_state(self):
        proposal = self.service.propose(1, "create_action_item", {"title": "Draft"})
        non_object = self.client.post(
            f"/api/agent/actions/{proposal['id']}/edit",
            data="[]",
            content_type="application/json",
        )
        wrong_user = self.client.post(
            f"/api/agent/actions/{proposal['id']}/cancel", json={"user_id": 2}
        )
        missing = self.client.get("/api/agent/actions/999999")
        self.client.post(f"/api/agent/actions/{proposal['id']}/cancel", json={})
        conflict = self.client.post(
            f"/api/agent/actions/{proposal['id']}/confirm", json={}
        )

        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(non_object.get_json()["error"]["code"], "invalid_request")
        self.assertEqual(wrong_user.status_code, 403)
        self.assertEqual(wrong_user.get_json()["error"]["code"], "forbidden")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["error"]["code"], "not_found")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["error"]["code"], "proposal_cancelled")


if __name__ == "__main__":
    unittest.main()

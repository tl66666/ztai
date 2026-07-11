import json
import os
import sqlite3
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

    def test_all_action_schemas_reject_unknown_and_invalid_values_before_persisting(self):
        with connect(self.db_path) as conn:
            opportunity_id = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Owned', 'Role')"
            ).lastrowid
            action_id = conn.execute(
                "INSERT INTO action_items (user_id, title) VALUES (1, 'Owned action')"
            ).lastrowid

        valid = {
            "set_career_goal": {"target_role": "Engineer"},
            "create_opportunity": {"company": "Acme", "job_title": "Engineer"},
            "create_resume_version": {
                "resume_id": self.resume_id,
                "content": "Resume content",
                "metadata": {"version_label": "v2", "source_type": "agent"},
            },
            "link_opportunity_resume": {
                "opportunity_id": opportunity_id,
                "resume_id": self.resume_id,
            },
            "create_interview_plan": {
                "opportunity_id": opportunity_id,
                "title": "Prepare",
            },
            "create_action_item": {"title": "Research"},
            "complete_action_item": {"action_id": action_id, "evidence": "done"},
            "update_opportunity": {
                "opportunity_id": opportunity_id,
                "changes": {"notes": "called"},
            },
            "save_career_report": {
                "report_type": "weekly",
                "content": {"summary": "progress"},
            },
        }
        for action_type, arguments in valid.items():
            unknown = json.loads(json.dumps(arguments))
            if action_type == "create_resume_version":
                unknown["metadata"]["unexpected"] = True
            elif action_type == "update_opportunity":
                unknown["changes"]["unexpected"] = True
            else:
                unknown["unexpected"] = True
            with self.subTest(action_type=action_type, kind="unknown"):
                with self.assertRaises(ValueError):
                    self.propose(action_type, unknown)

        invalid = {
            "set_career_goal": {
                "target_role": "Engineer",
                "salary": {"min": 30, "max": 20, "unexpected": 1},
            },
            "create_opportunity": {
                "company": "Acme",
                "job_title": "Engineer",
                "notes": 123,
            },
            "create_resume_version": {
                "resume_id": self.resume_id,
                "content": "x" * 1_000_001,
                "metadata": {},
            },
            "link_opportunity_resume": {
                "opportunity_id": 0,
                "resume_id": self.resume_id,
            },
            "create_interview_plan": {
                "opportunity_id": opportunity_id,
                "description": "x" * 20_001,
            },
            "create_action_item": {"title": "Research", "priority": True},
            "complete_action_item": {"action_id": action_id, "evidence": 42},
            "update_opportunity": {
                "opportunity_id": opportunity_id,
                "changes": {"contact_info": "x" * 2_001},
            },
            "save_career_report": {
                "report_type": "weekly",
                "title": 42,
                "content": {},
            },
        }
        for action_type, arguments in invalid.items():
            with self.subTest(action_type=action_type, kind="invalid"):
                with self.assertRaises(ValueError):
                    self.propose(action_type, arguments)

        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM agent_action_proposals"
                ).fetchone()[0],
                0,
            )

    def test_all_action_previews_redact_sensitive_values_and_edits_keep_identity_fixed(self):
        with connect(self.db_path) as conn:
            opportunity_id = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Owned', 'Role')"
            ).lastrowid
            action_id = conn.execute(
                "INSERT INTO action_items (user_id, title) VALUES (1, 'Owned action')"
            ).lastrowid

        secret = "DO-NOT-PREVIEW-SECRET"
        cases = {
            "set_career_goal": ({"target_role": "Engineer", "experience": secret}, {"user_id": 2}),
            "create_opportunity": (
                {"company": "Acme", "job_title": "Engineer", "jd_text": secret, "notes": secret, "contact_info": secret},
                {"user_id": 2},
            ),
            "create_resume_version": (
                {"resume_id": self.resume_id, "content": secret, "metadata": {"version_label": "v2", "source_type": "agent"}},
                {"resume_id": self.resume_id + 1},
            ),
            "link_opportunity_resume": (
                {"opportunity_id": opportunity_id, "resume_id": self.resume_id},
                {"opportunity_id": opportunity_id + 1},
            ),
            "create_interview_plan": (
                {"opportunity_id": opportunity_id, "title": "Prepare", "description": secret},
                {"opportunity_id": opportunity_id + 1},
            ),
            "create_action_item": (
                {"title": "Research", "description": secret},
                {"application_id": opportunity_id},
            ),
            "complete_action_item": (
                {"action_id": action_id, "evidence": secret},
                {"action_id": action_id + 1},
            ),
            "update_opportunity": (
                {"opportunity_id": opportunity_id, "changes": {"notes": secret, "contact_info": secret, "jd_text": secret}},
                {"opportunity_id": opportunity_id + 1},
            ),
            "save_career_report": (
                {"report_type": "weekly", "title": "Week", "content": {"summary": secret}},
                {"user_id": 2},
            ),
        }
        for action_type, (arguments, forbidden_edit) in cases.items():
            with self.subTest(action_type=action_type):
                proposal = self.propose(action_type, arguments)
                self.assertNotIn(secret, proposal["preview"])
                with self.assertRaisesRegex(ValueError, "edit"):
                    self.service.edit(1, proposal["id"], forbidden_edit)
                unchanged = self.service.get(1, proposal["id"])
                self.assertEqual(unchanged["action_type"], action_type)
                self.assertEqual(
                    unchanged["idempotency_key"], proposal["idempotency_key"]
                )

    def test_all_target_ids_are_owned_at_proposal_time(self):
        with connect(self.db_path) as conn:
            owned_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Owned', 'Role')"
            ).lastrowid
            foreign_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (2, 'Foreign', 'Role')"
            ).lastrowid
            foreign_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Foreign', 'secret')"
            ).lastrowid
            foreign_action = conn.execute(
                "INSERT INTO action_items (user_id, title) VALUES (2, 'Foreign')"
            ).lastrowid

        cases = {
            "create_opportunity": {"company": "Acme", "job_title": "Role", "resume_id": foreign_resume},
            "create_resume_version": {"resume_id": foreign_resume, "content": "content", "metadata": {}},
            "link_opportunity_resume": {"opportunity_id": owned_opportunity, "resume_id": foreign_resume},
            "create_interview_plan": {"opportunity_id": foreign_opportunity},
            "create_action_item": {"title": "Task", "opportunity_id": foreign_opportunity},
            "complete_action_item": {"action_id": foreign_action},
            "update_opportunity": {"opportunity_id": foreign_opportunity, "changes": {"notes": "no"}},
        }
        for action_type, arguments in cases.items():
            with self.subTest(action_type=action_type):
                with self.assertRaises(LookupError):
                    self.propose(action_type, arguments)

        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM agent_action_proposals"
                ).fetchone()[0],
                0,
            )

    def test_nested_schema_aliases_and_report_values_are_strictly_bounded(self):
        with connect(self.db_path) as conn:
            first_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'One', 'Role')"
            ).lastrowid
            second_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Two', 'Role')"
            ).lastrowid

        invalid = [
            ("set_career_goal", {"preferences": {"unexpected": True}}),
            ("set_career_goal", {"source_metadata": {"form": "agent"}}),
            (
                "create_action_item",
                {
                    "title": "Ambiguous",
                    "opportunity_id": first_opportunity,
                    "application_id": second_opportunity,
                },
            ),
            (
                "create_opportunity",
                {"company": "Acme", "job_title": "Role", "resume_id": 0},
            ),
            (
                "create_resume_version",
                {
                    "resume_id": self.resume_id,
                    "content": "content",
                    "metadata": {"application_id": 0},
                },
            ),
            (
                "save_career_report",
                {
                    "report_type": "weekly",
                    "content": {"summary": "x" * 20_001},
                },
            ),
            (
                "save_career_report",
                {
                    "report_type": "weekly",
                    "content": {"score": float("inf")},
                },
            ),
        ]
        for action_type, arguments in invalid:
            with self.subTest(action_type=action_type, arguments=arguments):
                with self.assertRaises(ValueError):
                    self.propose(action_type, arguments)

        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM agent_action_proposals"
                ).fetchone()[0],
                0,
            )

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
            receipt_payloads = [
                json.loads(row[0])["_agent_receipt"]
                for row in conn.execute(
                    "SELECT payload_json FROM domain_events WHERE source LIKE 'agent:%'"
                )
            ]
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
        self.assertEqual(
            {receipt["action_type"] for receipt in receipt_payloads},
            {
                "set_career_goal",
                "create_opportunity",
                "create_resume_version",
                "link_opportunity_resume",
                "create_interview_plan",
                "create_action_item",
                "complete_action_item",
                "update_opportunity",
                "save_career_report",
            },
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

    def test_recovers_after_business_commit_when_proposal_finalizer_crashes(self):
        from utils.agent_runtime.actions import ActionProposalService

        proposal = self.propose(
            "create_action_item", {"title": "Crash recovery"}
        )
        with patch.object(
            self.service,
            "_finalize_completed",
            side_effect=sqlite3.OperationalError("simulated finalizer crash"),
            create=True,
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "finalizer crash"):
                self.service.confirm(1, proposal["id"])

        with connect(self.db_path) as conn:
            state_after_crash = conn.execute(
                "SELECT status FROM agent_action_proposals WHERE id = ?",
                (proposal["id"],),
            ).fetchone()[0]
            business_count = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE title = 'Crash recovery'"
            ).fetchone()[0]
        self.assertEqual(state_after_crash, "executing")
        self.assertEqual(business_count, 1)

        recovered_service = ActionProposalService(self.db_path, local_user_id=1)
        recovered = recovered_service.confirm(1, proposal["id"])

        self.assertEqual(recovered["status"], "completed")
        self.assertEqual(recovered["result"]["entity_type"], "action_item")
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM action_items WHERE title = 'Crash recovery'"
                ).fetchone()[0],
                1,
            )
            receipts = conn.execute(
                "SELECT source, payload_json FROM domain_events WHERE source LIKE 'agent:%'"
            ).fetchall()
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0]["payload_json"])["_agent_receipt"]
        self.assertEqual(receipt.pop("action_type"), "create_action_item")
        self.assertEqual(receipt, recovered["result"])

    def test_fresh_executing_without_receipt_conflicts_and_stale_retries(self):
        proposal = self.propose(
            "create_action_item", {"title": "Lease retry"}
        )
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE agent_action_proposals
                SET status = 'executing', executing_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (proposal["id"],),
            )

        with self.assertRaises(self.error_type) as fresh:
            self.service.confirm(1, proposal["id"])
        self.assertEqual(fresh.exception.code, "proposal_executing")

        stale_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agent_action_proposals SET executing_at = ? WHERE id = ?",
                (stale_at, proposal["id"]),
            )

        completed = self.service.confirm(1, proposal["id"])
        self.assertEqual(completed["status"], "completed")
        with connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE title = 'Lease retry'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_independent_service_instances_converge_without_duplicate_writes(self):
        from utils.agent_runtime.actions import ActionProposalService

        proposal = self.propose(
            "create_action_item", {"title": "Cross instance"}
        )
        services = [
            ActionProposalService(self.db_path, local_user_id=1),
            ActionProposalService(self.db_path, local_user_id=1),
        ]
        for service in services:
            service._proposal_lock = lambda _proposal_id: threading.Lock()
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def confirm(service):
            try:
                barrier.wait()
                results.append(service.confirm(1, proposal["id"]))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=confirm, args=(service,)) for service in services
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        final = services[0].confirm(1, proposal["id"])
        self.assertEqual(final["status"], "completed")
        self.assertTrue(results or errors)
        self.assertTrue(
            all(
                isinstance(error, self.error_type)
                and error.code == "proposal_executing"
                for error in errors
            )
        )
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM action_items WHERE title = 'Cross instance'"
                ).fetchone()[0],
                1,
            )

    def test_stale_retry_receipt_rolls_back_late_original_executor(self):
        from utils.agent_runtime.actions import ActionProposalService

        proposal = self.propose(
            "create_action_item", {"title": "Lease overlap"}
        )
        original = ActionProposalService(self.db_path, local_user_id=1)
        retry = ActionProposalService(self.db_path, local_user_id=1)
        original._proposal_lock = lambda _proposal_id: threading.Lock()
        retry._proposal_lock = lambda _proposal_id: threading.Lock()
        entered = threading.Event()
        release = threading.Event()
        original_execute = original._execute
        results = []
        errors = []

        def blocked_execute(*args, **kwargs):
            entered.set()
            release.wait(timeout=5)
            return original_execute(*args, **kwargs)

        original._execute = blocked_execute

        def run_original():
            try:
                results.append(original.confirm(1, proposal["id"]))
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=run_original)
        thread.start()
        self.assertTrue(entered.wait(timeout=5))
        stale_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agent_action_proposals SET executing_at = ? WHERE id = ?",
                (stale_at, proposal["id"]),
            )

        retry_result = retry.confirm(1, proposal["id"])
        release.set()
        thread.join(timeout=5)

        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(retry_result["status"], "completed")
        self.assertEqual(results[0]["result"], retry_result["result"])
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM action_items WHERE title = 'Lease overlap'"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM domain_events WHERE source LIKE 'agent:%'"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM domain_events WHERE source LIKE 'agent:%'"
                ).fetchone()[0],
                1,
            )

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

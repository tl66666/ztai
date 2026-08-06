import json
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.agent_api_client import create_agent_test_runtime
from utils.agent_runtime.actions import ActionProposalError
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
        import gc, shutil
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temp_dir.name, ignore_errors=True)
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

    def test_integer_fields_never_truncate_or_coerce_non_integers(self):
        invalid = [
            ("create_action_item", {"title": "x", "priority": True}),
            ("create_action_item", {"title": "x", "priority": 1.25}),
            ("create_action_item", {"title": "x", "priority": "1.0"}),
            ("create_opportunity", {"company": "A", "job_title": "B", "salary_min": False}),
            ("create_opportunity", {"company": "A", "job_title": "B", "salary_min": 2.9}),
            ("create_resume_version", {"resume_id": 1.0, "content": "x", "metadata": {}}),
        ]
        for action_type, arguments in invalid:
            with self.subTest(action_type=action_type, arguments=arguments):
                with self.assertRaises(ValueError):
                    self.propose(action_type, arguments)

        accepted = self.propose(
            "create_opportunity",
            {"company": "A", "job_title": "B", "salary_min": "12"},
        )
        self.assertEqual(accepted["arguments"]["salary_min"], 12)

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

    def test_report_action_link_is_owned_pending_typed_and_frozen(self):
        from utils.agent_runtime.actions import career_action_tool_schema

        with connect(self.db_path) as conn:
            valid_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (1,'Save report','career_report','pending')"
            ).lastrowid
            wrong_type_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (1,'Follow up','follow_up','pending')"
            ).lastrowid
            completed_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (1,'Done report','career_report','completed')"
            ).lastrowid
            in_progress_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (1,'Started report','career_report','in_progress')"
            ).lastrowid
            foreign_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (2,'Foreign report','career_report','pending')"
            ).lastrowid
        base = {"report_type": "weekly", "content": {"summary": "progress"}}
        proposal = self.propose("save_career_report", {**base, "action_id": valid_id})
        self.assertEqual(proposal["arguments"]["action_id"], valid_id)
        with self.assertRaisesRegex(ValueError, "not allowed"):
            self.service.edit(1, proposal["id"], {"action_id": wrong_type_id})
        for invalid_id in (wrong_type_id, completed_id, in_progress_id, foreign_id):
            with self.subTest(action_id=invalid_id), self.assertRaises((LookupError, ValueError)):
                self.propose("save_career_report", {**base, "action_id": invalid_id})
        report_branch = next(
            branch for branch in career_action_tool_schema()["oneOf"]
            if branch["properties"]["action_type"].get("const") == "save_career_report"
        )
        self.assertIn("action_id", report_branch["properties"]["arguments"]["properties"])

    def test_resume_action_link_is_owned_related_active_and_frozen(self):
        with connect(self.db_path) as conn:
            opportunity_id = conn.execute(
                "INSERT INTO job_applications (user_id,company,job_title) VALUES (1,'Acme','Engineer')"
            ).lastrowid
            other_opportunity_id = conn.execute(
                "INSERT INTO job_applications (user_id,company,job_title) VALUES (1,'Other','Engineer')"
            ).lastrowid
            action_id = conn.execute(
                "INSERT INTO action_items (user_id,application_id,title,action_type,status) "
                "VALUES (1,?,'Resume','resume_version','pending')",
                (opportunity_id,),
            ).lastrowid
            wrong_link_id = conn.execute(
                "INSERT INTO action_items (user_id,application_id,title,action_type,status) "
                "VALUES (1,?,'Other resume','resume_version','pending')",
                (other_opportunity_id,),
            ).lastrowid
        arguments = {
            "resume_id": self.resume_id,
            "content": "tailored",
            "metadata": {"application_id": opportunity_id, "action_id": action_id},
        }
        proposal = self.propose("create_resume_version", arguments)
        with self.assertRaisesRegex(ValueError, "not allowed"):
            self.service.edit(
                1, proposal["id"], {"metadata": {"action_id": wrong_link_id}}
            )
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.propose(
                "create_resume_version",
                {**arguments, "metadata": {"application_id": opportunity_id, "action_id": wrong_link_id}},
            )

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

    def test_nested_relationship_retarget_edits_are_rejected_without_mutation(self):
        with connect(self.db_path) as conn:
            first_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'One', 'Role')"
            ).lastrowid
            second_opportunity = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Two', 'Role')"
            ).lastrowid
            second_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Other', 'private')"
            ).lastrowid

        resume_proposal = self.propose(
            "create_resume_version",
            {
                "resume_id": self.resume_id,
                "content": "original content",
                "metadata": {
                    "version_label": "v2",
                    "application_id": first_opportunity,
                },
            },
        )
        with self.assertRaisesRegex(ValueError, "edit"):
            self.service.edit(
                1,
                resume_proposal["id"],
                {"metadata": {"application_id": second_opportunity}},
            )
        self.assertEqual(
            self.service.get(1, resume_proposal["id"]), resume_proposal
        )

        edited_resume = self.service.edit(
            1,
            resume_proposal["id"],
            {"content": "revised content", "metadata": {"version_label": "v3"}},
        )
        self.assertEqual(edited_resume["arguments"]["resume_id"], self.resume_id)
        self.assertEqual(
            edited_resume["arguments"]["metadata"]["application_id"],
            first_opportunity,
        )
        self.assertEqual(
            edited_resume["idempotency_key"], resume_proposal["idempotency_key"]
        )

        opportunity_proposal = self.propose(
            "update_opportunity",
            {
                "opportunity_id": first_opportunity,
                "changes": {"resume_id": self.resume_id, "notes": "original"},
            },
        )
        with self.assertRaisesRegex(ValueError, "edit"):
            self.service.edit(
                1, opportunity_proposal["id"], {"resume_id": second_resume}
            )
        self.assertEqual(
            self.service.get(1, opportunity_proposal["id"]), opportunity_proposal
        )

        edited_opportunity = self.service.edit(
            1, opportunity_proposal["id"], {"notes": "safe revision"}
        )
        self.assertEqual(
            edited_opportunity["arguments"]["opportunity_id"], first_opportunity
        )
        self.assertEqual(
            edited_opportunity["arguments"]["changes"]["resume_id"], self.resume_id
        )
        self.assertEqual(
            edited_opportunity["idempotency_key"],
            opportunity_proposal["idempotency_key"],
        )

    def test_previews_identify_relationship_targets_without_sensitive_content(self):
        with connect(self.db_path) as conn:
            opportunity_id = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (1, 'Owned', 'Role')"
            ).lastrowid

        cases = [
            (
                "create_opportunity",
                {
                    "company": "Acme",
                    "job_title": "Engineer",
                    "resume_id": self.resume_id,
                    "jd_text": "SECRET-JD",
                },
                "新增投递",
                {"resume_id": self.resume_id},
            ),
            (
                "create_resume_version",
                {
                    "resume_id": self.resume_id,
                    "content": "SECRET-RESUME",
                    "metadata": {"application_id": opportunity_id},
                },
                "创建新简历版本",
                {"resume_id": self.resume_id, "application_id": opportunity_id},
            ),
            (
                "create_action_item",
                {
                    "title": "Research",
                    "opportunity_id": opportunity_id,
                    "description": "SECRET-ACTION",
                },
                "新增行动任务",
                {"opportunity_id": opportunity_id},
            ),
            (
                "update_opportunity",
                {
                    "opportunity_id": opportunity_id,
                    "changes": {
                        "resume_id": self.resume_id,
                        "notes": "SECRET-NOTES",
                    },
                },
                "更新当前投递信息",
                {"opportunity_id": opportunity_id, "resume_id": self.resume_id},
            ),
        ]
        for action_type, arguments, label, targets in cases:
            with self.subTest(action_type=action_type):
                proposal = self.propose(action_type, arguments)
                preview = proposal["preview"]
                self.assertIn(label, preview)
                self.assertNotIn("SECRET", preview)
                self.assertEqual(self.service.public(proposal)["target_ids"], targets)

    def test_non_string_json_keys_are_rejected_recursively_before_persistence(self):
        invalid_payloads = [
            (
                "save_career_report",
                {
                    "report_type": "weekly",
                    "content": {"items": [{1: "numeric", "1": "string"}]},
                },
            ),
            (
                "save_career_report",
                {"report_type": "weekly", "content": {"nested": [{True: "x"}]}},
            ),
            (
                "create_resume_version",
                {
                    "resume_id": self.resume_id,
                    "content": "content",
                    "metadata": {1: "invalid"},
                },
            ),
            (
                "set_career_goal",
                {1: "numeric", "1": "string", "target_role": "Engineer"},
            ),
        ]
        for action_type, arguments in invalid_payloads:
            with self.subTest(action_type=action_type):
                with self.assertRaisesRegex(ValueError, "field name"):
                    self.propose(action_type, arguments)

        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM agent_action_proposals"
                ).fetchone()[0],
                0,
            )

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
            with self.assertRaises(self.error_type) as raised:
                self.service.confirm(1, proposal["id"])
        self.assertEqual(raised.exception.code, "execution_uncertain")

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

    def test_edit_and_confirm_use_one_atomic_argument_snapshot(self):
        from utils.agent_runtime.actions import ActionProposalService

        for claim_wins in (False, True):
            with self.subTest(claim_wins=claim_wins):
                proposal = self.propose("create_action_item", {"title": "before"})
                claimed = threading.Event()
                edit_started = threading.Event()
                release = threading.Event()

                def failpoint(_proposal):
                    claimed.set()
                    release.wait(timeout=5)

                confirming = ActionProposalService(
                    self.db_path,
                    local_user_id=1,
                    claim_failpoint=failpoint if claim_wins else None,
                )
                editing = ActionProposalService(self.db_path, local_user_id=1)
                outcomes = {}

                def confirm():
                    outcomes["confirm"] = confirming.confirm(1, proposal["id"])

                def edit():
                    edit_started.set()
                    try:
                        outcomes["edit"] = editing.edit(
                            1, proposal["id"], {"title": "after"}
                        )
                    except Exception as exc:
                        outcomes["edit_error"] = exc

                if claim_wins:
                    confirm_thread = threading.Thread(target=confirm)
                    confirm_thread.start()
                    self.assertTrue(claimed.wait(timeout=5))
                    edit_thread = threading.Thread(target=edit)
                    edit_thread.start()
                    self.assertTrue(edit_started.wait(timeout=5))
                    release.set()
                else:
                    edit_thread = threading.Thread(target=edit)
                    edit_thread.start()
                    edit_thread.join(timeout=5)
                    confirm_thread = threading.Thread(target=confirm)
                    confirm_thread.start()

                confirm_thread.join(timeout=5)
                edit_thread.join(timeout=5)
                self.assertFalse(confirm_thread.is_alive())
                self.assertFalse(edit_thread.is_alive())
                stored = self.service.get(1, proposal["id"])
                with connect(self.db_path) as conn:
                    item = conn.execute(
                        "SELECT title FROM action_items WHERE id = ?",
                        (stored["result"]["id"],),
                    ).fetchone()
                if claim_wins:
                    self.assertIsInstance(outcomes.get("edit_error"), self.error_type)
                    self.assertEqual(item["title"], "before")
                else:
                    self.assertEqual(outcomes["edit"]["arguments"]["title"], "after")
                    self.assertEqual(item["title"], "after")

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
        self.db_path = os.path.join(self.temp_dir.name, "api-actions.db")
        self.client_context, self.client = create_agent_test_runtime(
            self.temp_dir.name,
            db_name="api-actions.db",
        )
        self.client_context.__enter__()
        self.container = self.client_context.app.state.container
        self.service = self.container.agent.action_service

    def test_execution_failure_uses_a_clear_chinese_message(self):
        action = self.service.propose(1, "create_action_item", {"title": "测试失败提示"})
        with patch.object(
            self.service, "confirm",
            side_effect=ActionProposalError("execution_failed", "action execution failed", 500),
        ):
            response = self.client.post(
                f"/api/agent/actions/{action['id']}/confirm", json={}
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["error"]["code"], "execution_failed")
        self.assertEqual(payload["error"]["message"], "暂时无法保存这项操作，请稍后重试。")

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
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
        self.assertEqual(edited.get_json()["action"]["editable"]["title"], "Final")
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
        self.assertEqual(wrong_user.status_code, 400)
        self.assertEqual(wrong_user.get_json()["error"]["code"], "user_id_not_allowed")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["error"]["code"], "not_found")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["error"]["code"], "proposal_cancelled")

    def test_action_api_uses_server_identity_and_cannot_read_foreign_proposal(self):
        own = self.service.propose(1, "create_action_item", {"title": "Own"})
        with connect(self.db_path) as conn:
            foreign_id = conn.execute(
                """
                INSERT INTO agent_action_proposals
                    (user_id, action_type, payload_json, arguments_json, preview,
                     status, risk_level, expires_at, idempotency_key)
                VALUES (2, 'create_action_item', '{}', '{}', 'foreign',
                        'pending', 'low', '2999-01-01T00:00:00+00:00', 'foreign-key')
                """
            ).lastrowid

        query_spoof = self.client.get(
            f"/api/agent/actions/{own['id']}?user_id=2"
        )
        body_spoof = self.client.post(
            f"/api/agent/actions/{own['id']}/cancel", json={"user_id": 2}
        )
        for response in (query_spoof, body_spoof):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.get_json()["error"]["code"], "user_id_not_allowed"
            )
        foreign = self.client.get(f"/api/agent/actions/{foreign_id}")
        self.assertEqual(foreign.status_code, 403)
        self.assertEqual(foreign.get_json()["error"]["code"], "forbidden")

    def test_public_action_dto_redacts_sensitive_arguments(self):
        secret = "secret@example.test resume and JD evidence"
        proposal = self.service.propose(
            1,
            "create_opportunity",
            {
                "company": "Acme",
                "job_title": "Engineer",
                "jd_text": secret,
                "contact_info": secret,
                "notes": secret,
                "salary_min": 10,
            },
        )
        payloads = [
            self.client.get("/api/agent/actions").get_json(),
            self.client.get(f"/api/agent/actions/{proposal['id']}").get_json(),
            self.client.post(
                f"/api/agent/actions/{proposal['id']}/edit",
                json={"company": "Better"},
            ).get_json(),
        ]
        cancellable = self.service.propose(
            1, "create_action_item", {"title": "Cancel", "description": secret}
        )
        confirmable = self.service.propose(
            1, "create_action_item", {"title": "Confirm", "description": secret}
        )
        payloads.extend(
            [
                self.client.post(
                    f"/api/agent/actions/{cancellable['id']}/cancel", json={}
                ).get_json(),
                self.client.post(
                    f"/api/agent/actions/{confirmable['id']}/confirm", json={}
                ).get_json(),
            ]
        )
        serialized = json.dumps(payloads)
        self.assertNotIn(secret, serialized)
        self.assertNotIn('"arguments"', serialized)
        action = payloads[2]["action"]
        self.assertEqual(action["editable"]["company"], "Better")
        self.assertEqual(action["action_type"], "create_opportunity")
        self.assertIn("created_at", action)

    def test_state_changes_require_json_and_reject_foreign_origins(self):
        for endpoint in ("edit", "confirm", "cancel"):
            proposal = self.service.propose(
                1, "create_action_item", {"title": endpoint}
            )
            url = f"/api/agent/actions/{proposal['id']}/{endpoint}"
            body = {"title": "edited"} if endpoint == "edit" else {}
            foreign = self.client.post(
                url, json=body, headers={"Origin": "https://evil.example"}
            )
            form = self.client.post(url, data=body)
            allowed = self.client.post(
                url, json=body, headers={"Origin": "http://localhost:5000"}
            )
            self.assertEqual(foreign.status_code, 403)
            self.assertEqual(form.status_code, 400)
            self.assertEqual(allowed.status_code, 200)
            self.assertNotEqual(
                allowed.headers.get("Access-Control-Allow-Origin"), "*"
            )
            self.assertEqual(
                allowed.headers.get("Access-Control-Allow-Origin"),
                "http://localhost:5000",
            )

    def test_unexpected_exception_is_logged_and_returned_without_secret(self):
        secret = "database password top-secret"
        proposal = self.service.propose(1, "create_action_item", {"title": "x"})
        with patch.object(
            self.service, "confirm", side_effect=RuntimeError(secret)
        ), patch("backend.api.agent._LOGGER.exception") as logged:
            response = self.client.post(
                f"/api/agent/actions/{proposal['id']}/confirm", json={}
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertNotIn(secret, response.get_data(as_text=True))
        logged.assert_called_once()

    def test_finalizer_failure_is_uncertain_and_next_confirm_recovers_once(self):
        secret = "proposal finalizer secret"
        proposal = self.service.propose(1, "create_action_item", {"title": "once"})
        original = self.service._finalize_completed
        with patch.object(
            self.service, "_finalize_completed", side_effect=RuntimeError(secret)
        ), patch("backend.api.agent._LOGGER.exception") as logged:
            response = self.client.post(
                f"/api/agent/actions/{proposal['id']}/confirm", json={}
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"]["code"], "execution_uncertain"
        )
        self.assertNotIn(secret, response.get_data(as_text=True))
        logged.assert_called_once()
        public = self.client.get(
            f"/api/agent/actions/{proposal['id']}"
        ).get_data(as_text=True)
        self.assertNotIn(secret, public)
        self.service._finalize_completed = original
        recovered = self.client.post(
            f"/api/agent/actions/{proposal['id']}/confirm", json={}
        )
        self.assertEqual(recovered.status_code, 200)
        with connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE title = 'once'"
            ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()

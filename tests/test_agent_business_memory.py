import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from utils.agent_runtime.context import ContextBuilder
from utils.agent_runtime.memory import MemoryStore, create_agent_tables
from utils.domain.career import CareerService
from utils.domain.database import connect, migrate_database
from utils.domain.events import apply_event_to_actions
from utils.domain.interviews import InterviewService


class AgentBusinessMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "business-memory.db")
        migrate_database(self.db_path)
        with connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, resume_id INTEGER,
                    job_title TEXT, conversation TEXT, score INTEGER, feedback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        create_agent_tables(self.db_path)
        self.store = MemoryStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_memories_ranks_entity_match_and_never_crosses_user(self):
        old_id = self.store.upsert_memory(
            1, "semantic", "preference", "target_role", "Backend Engineer", 0.9,
            "confirmed", related_entity_type="opportunity", related_entity_id="41",
        )
        new_id = self.store.upsert_memory(
            1, "semantic", "preference", "city", "Backend roles in Hangzhou", 0.9,
            "candidate", related_entity_type="opportunity", related_entity_id="42",
        )
        self.store.upsert_memory(
            2, "semantic", "preference", "target_role", "Backend Engineer secret", 1.0,
            "confirmed", related_entity_type="opportunity", related_entity_id="41",
        )

        results = self.store.search_memories(1, "opportunity 41 Backend", kind="semantic", limit=5)

        self.assertEqual(results[0]["id"], old_id)
        self.assertIn(new_id, [row["id"] for row in results])
        self.assertTrue(all(row["user_id"] == 1 for row in results))

    def test_search_handles_punctuation_chinese_and_forced_fts_fallback(self):
        memory_id = self.store.upsert_memory(
            1, "episodic", "interview", "mock", {"input": "字节跳动 C++", "result": "复盘沟通"},
            0.8, "confirmed",
        )
        with patch.object(
            self.store, "_fts_matches", side_effect=sqlite3.OperationalError("no fts5")
        ):
            results = self.store.search_memories(
                1, '字节跳动 (C++) OR "oops"?', kind="episodic", statuses=("confirmed",)
            )
        self.assertEqual([row["id"] for row in results], [memory_id])

    def test_fts_backfill_supersede_and_delete_stay_consistent(self):
        memory_id = self.store.upsert_memory(
            1, "semantic", "preference", "target_city", "Shanghai", 0.9, "confirmed"
        )
        create_agent_tables(self.db_path)
        if not self.store.fts_available():
            self.skipTest("SQLite was built without FTS5")
        self.assertEqual(
            self.store.search_memories(1, "Shanghai", kind="semantic")[0]["id"], memory_id
        )
        replacement = self.store.upsert_memory(
            1, "semantic", "preference", "target_city", "杭州", 0.95, "confirmed"
        )
        self.assertEqual(
            [row["id"] for row in self.store.search_memories(1, "杭州", kind="semantic")],
            [replacement],
        )
        self.store.delete_memory(1, replacement)
        self.assertEqual(self.store.search_memories(1, "杭州", kind="semantic"), [])

    def test_context_snapshot_is_private_ranked_bounded_and_corruption_tolerant(self):
        career = CareerService(self.db_path)
        career.upsert_profile(
            1,
            {
                "career_direction": "software",
                "target_role": "Backend Engineer",
                "cities": ["Hangzhou"],
                "salary": {"min": 20, "max": 30},
                "experience": "3 years",
                "confirmed_skills": ["PRIVATE-SKILL"],
                "constraints": ["PRIVATE-CONSTRAINT"],
            },
        )
        with connect(self.db_path) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes (user_id,title,content,status,version_label,target_job_title) "
                "VALUES (1,'Main Resume','PRIVATE-CONTENT','active','v3','Backend Engineer')"
            ).lastrowid
        opportunity = career.create_opportunity(
            1,
            {
                "company": "Acme",
                "job_title": "Backend Engineer",
                "status": "一面",
                "city": "Hangzhou",
                "resume_id": resume_id,
                "priority": 9,
                "jd_text": "PRIVATE-JD",
                "notes": "PRIVATE-NOTES",
                "contact_info": "PRIVATE-CONTACT",
            },
        )
        career.create_action_item(
            1,
            {"opportunity_id": opportunity["id"], "title": "Prepare system design", "type": "interview_plan"},
        )
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO interviews (user_id,resume_id,job_title,conversation,score,feedback) "
                "VALUES (1,?,?,?,20,?)",
                (resume_id, "Backend Engineer", "PRIVATE-ANSWER", "PRIVATE-FEEDBACK"),
            )
            conn.execute(
                "INSERT INTO domain_events (user_id,aggregate_type,aggregate_id,event_type,payload_json) "
                "VALUES (1,'opportunity',?,'opportunity.updated','not-json')",
                (str(opportunity["id"]),),
            )
        conversation = self.store.create_conversation(1, "Context")

        snapshot = ContextBuilder(self.store, self.db_path).build(
            1, conversation.id, f"What happened at Acme opportunity {opportunity['id']}?"
        ).career_snapshot

        self.assertLessEqual(len(snapshot), 8000)
        for secret in (
            "PRIVATE-CONTENT", "PRIVATE-JD", "PRIVATE-NOTES", "PRIVATE-CONTACT",
            "PRIVATE-ANSWER", "PRIVATE-FEEDBACK", "PRIVATE-SKILL", "PRIVATE-CONSTRAINT",
        ):
            self.assertNotIn(secret, snapshot)
        for expected in ("Acme", "Backend Engineer", "Main Resume", "Prepare system design", "20", "opportunity.updated"):
            self.assertIn(expected, snapshot)
        self.assertLess(snapshot.index("Acme"), snapshot.find("opportunities") + 1000)

    def test_event_mapper_completes_only_exact_linked_actions_and_is_idempotent(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        exact = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Version", "type": "resume_version"}
        )
        wrong = career.create_action_item(1, {"title": "Unlinked", "type": "resume_version"})
        generic = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Generic", "type": "follow_up"}
        )
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            apply_event_to_actions(
                conn, 1, "resume.version_created", "opportunity", opportunity["id"], {"resume_id": 7}
            )
            apply_event_to_actions(
                conn, 1, "resume.version_created", "opportunity", opportunity["id"], {"resume_id": 7}
            )
        rows = {row["id"]: row for row in career.list_action_items(1)}
        self.assertEqual(rows[exact["id"]]["status"], "completed")
        self.assertEqual(rows[wrong["id"]]["status"], "pending")
        self.assertEqual(rows[generic["id"]]["status"], "pending")
        self.assertIn("resume.version_created", rows[exact["id"]]["completion_evidence"])
        self.assertEqual(rows[exact["id"]]["source"], "domain_event")

    def test_event_and_auto_completion_share_transaction_and_context_sees_result(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        with connect(self.db_path) as conn:
            source_resume = conn.execute(
                "INSERT INTO resumes (user_id,title,content) VALUES (1,'Base','content')"
            ).lastrowid
        action = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Create tailored resume", "type": "create_resume_version"}
        )
        with patch("utils.domain.career.apply_event_to_actions", side_effect=RuntimeError("feedback failed")):
            with self.assertRaisesRegex(RuntimeError, "feedback failed"):
                career.create_resume_version(
                    1, source_resume, "tailored", {"application_id": opportunity["id"]}
                )
        self.assertEqual(career.list_action_items(1)[0]["status"], "pending")
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='resume.version_created'").fetchone()[0],
                0,
            )
        career.create_resume_version(
            1, source_resume, "tailored", {"application_id": opportunity["id"]}
        )
        conversation = self.store.create_conversation(1, "After event")
        snapshot = ContextBuilder(self.store, self.db_path).build(1, conversation.id, "actions").career_snapshot
        self.assertIn("Create tailored resume", snapshot)
        self.assertIn("completed", snapshot)
        self.assertEqual(career.list_action_items(1)[0]["id"], action["id"])

    def test_interview_and_report_writers_complete_only_their_action_types(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        interview_action = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Mock", "type": "mock_interview"}
        )
        report_action = career.create_action_item(1, {"title": "Save report", "type": "career_report"})
        with connect(self.db_path) as conn:
            session_id = conn.execute(
                "INSERT INTO interview_sessions (user_id,application_id,job_title) VALUES (1,?,'Engineer')",
                (opportunity["id"],),
            ).lastrowid
            InterviewService(self.db_path)._write_event(
                conn, session_id, "interview.completed", {"score": 77}
            )
        statuses = {row["id"]: row["status"] for row in career.list_action_items(1)}
        self.assertEqual(statuses[interview_action["id"]], "completed")
        self.assertEqual(statuses[report_action["id"]], "pending")

        career.save_report(
            1, {"report_type": "weekly", "title": "Week", "content": {"score": 77}}
        )
        statuses = {row["id"]: row["status"] for row in career.list_action_items(1)}
        self.assertEqual(statuses[report_action["id"]], "completed")


if __name__ == "__main__":
    unittest.main()

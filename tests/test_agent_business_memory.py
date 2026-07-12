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

    def test_chinese_partial_overlap_beats_unrelated_high_confidence_padding(self):
        relevant_id = self.store.upsert_memory(
            1, "semantic", "preference", "target_role", "后端开发", 0.7, "candidate"
        )
        unrelated_id = self.store.upsert_memory(
            1, "semantic", "preference", "alternative_role", "前端岗位", 1.0, "confirmed"
        )
        for force_fallback in (False, True):
            manager = (
                patch.object(
                    self.store, "_fts_matches",
                    side_effect=sqlite3.OperationalError("forced fallback"),
                )
                if force_fallback
                else patch.object(self.store, "_fts_matches", wraps=self.store._fts_matches)
            )
            with manager:
                results = self.store.search_memories(1, "想找后端岗位！", kind="semantic")
            self.assertEqual(results[0]["id"], relevant_id)
            self.assertIn(unrelated_id, [row["id"] for row in results])

    def test_search_deduplicates_semantic_and_episodic_identity_in_fts_and_fallback(self):
        self.store.upsert_memory(
            1, "semantic", "preference", "target_role", " 后端开发 ", 0.7, "candidate"
        )
        best_semantic = self.store.upsert_memory(
            1, "semantic", "preference", "target_role", "后端开发", 0.9, "confirmed"
        )
        self.store.upsert_memory(
            1, "episodic", "interview", "attempt-1", {"input": "Acme", "result": "pass"},
            0.5, "candidate", related_entity_type="opportunity", related_entity_id="9",
        )
        best_episode = self.store.upsert_memory(
            1, "episodic", "interview", "attempt-2", {"result": "pass", "input": "Acme"},
            0.8, "confirmed", related_entity_type="opportunity", related_entity_id="9",
        )
        for force_fallback in (False, True):
            manager = (
                patch.object(self.store, "_fts_matches", side_effect=sqlite3.OperationalError("fallback"))
                if force_fallback else patch.object(self.store, "_fts_matches", wraps=self.store._fts_matches)
            )
            with manager:
                semantic = self.store.search_memories(1, "后端岗位", kind="semantic")
                episodic = self.store.search_memories(1, "Acme", kind="episodic")
            self.assertEqual([row["id"] for row in semantic].count(best_semantic), 1)
            self.assertEqual(len([row for row in semantic if row["memory_key"] == "target_role"]), 1)
            self.assertEqual([row["id"] for row in episodic], [best_episode])

    def test_search_preserves_identical_memories_for_distinct_entities(self):
        semantic_ids = [
            self.store.upsert_memory(
                1, "semantic", "fit", "assessment", "Strong backend fit", 0.9,
                "confirmed", related_entity_type="opportunity", related_entity_id=entity_id,
            )
            for entity_id in (41, 42)
        ]
        episodic_ids = [
            self.store.upsert_memory(
                1, "episodic", "match", "run", {"result": "Strong backend fit"}, 0.8,
                "confirmed", related_entity_type="opportunity", related_entity_id=entity_id,
            )
            for entity_id in (41, 42)
        ]
        for force_fallback in (False, True):
            manager = (
                patch.object(
                    self.store, "_fts_matches", side_effect=sqlite3.OperationalError("fallback")
                )
                if force_fallback else patch.object(
                    self.store, "_fts_matches", wraps=self.store._fts_matches
                )
            )
            with manager:
                semantic = self.store.search_memories(
                    1, "opportunity 41 backend", kind="semantic"
                )
                episodic = self.store.search_memories(
                    1, "opportunity 42 backend", kind="episodic"
                )
            self.assertEqual(semantic[0]["id"], semantic_ids[0])
            self.assertEqual({row["id"] for row in semantic}, set(semantic_ids))
            self.assertEqual(episodic[0]["id"], episodic_ids[1])
            self.assertEqual({row["id"] for row in episodic}, set(episodic_ids))

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

    def test_search_materializes_a_bounded_candidate_window_at_scale(self):
        timestamp = "2026-01-01T00:00:00+00:00"
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO agent_memories
                    (user_id,kind,category,memory_key,value_json,confidence,status,created_at,updated_at)
                VALUES (1,'semantic','scale',?, ?,0.5,'confirmed',?,?)
                """,
                [
                    (f"key-{index}", json.dumps(f"memory {index}"), timestamp, timestamp)
                    for index in range(3000)
                ],
            )
        target_id = self.store.upsert_memory(
            1, "semantic", "role", "target", "后端开发", 0.9, "confirmed"
        )
        create_agent_tables(self.db_path)
        if self.store.fts_available():
            with connect(self.db_path) as conn:
                searchable = conn.execute(
                    "SELECT searchable FROM agent_memories_fts WHERE memory_id = ?", (target_id,)
                ).fetchone()[0]
            self.assertRegex(searchable, r"(?:^|\s)后端(?:\s|$)")
            self.assertEqual(
                self.store.search_memories(1, "后端岗位", kind="semantic")[0]["id"], target_id
            )
            self.assertLessEqual(self.store._last_search_candidate_count, 500)
        with patch.object(
            self.store, "_fts_matches", side_effect=sqlite3.OperationalError("fallback")
        ):
            self.store.search_memories(1, "no exact match", kind="semantic")
        self.assertLessEqual(self.store._last_search_candidate_count, 500)

    def test_bounded_candidate_budgets_preserve_old_relevant_and_entity_rows(self):
        old_time = "2020-01-01T00:00:00+00:00"
        new_time = "2026-01-01T00:00:00+00:00"
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO agent_memories
                    (user_id,kind,category,memory_key,value_json,confidence,status,
                     related_entity_type,related_entity_id,created_at,updated_at)
                VALUES (1,'semantic','role',?, ?,0.8,'confirmed',NULL,NULL,?,?)
                """,
                [
                    (f"generic-{index}", json.dumps(f"backend role {index}"), new_time, new_time)
                    for index in range(400)
                ],
            )
            needle_id = conn.execute(
                """
                INSERT INTO agent_memories
                    (user_id,kind,category,memory_key,value_json,confidence,status,created_at,updated_at)
                VALUES (1,'semantic','archive','needle',?,0.7,'confirmed',?,?)
                """,
                (json.dumps("unique-needle-value"), old_time, old_time),
            ).lastrowid
            entity_id = conn.execute(
                """
                INSERT INTO agent_memories
                    (user_id,kind,category,memory_key,value_json,confidence,status,
                     related_entity_type,related_entity_id,created_at,updated_at)
                VALUES (1,'semantic','role','entity-fit',?,0.7,'confirmed','opportunity','41',?,?)
                """,
                (json.dumps("backend role"), old_time, old_time),
            ).lastrowid
        create_agent_tables(self.db_path)
        if self.store.fts_available():
            native = self.store.search_memories(
                1, "role unique-needle-value", kind="semantic", limit=8
            )
            self.assertIn(needle_id, [row["id"] for row in native])
            self.assertLessEqual(self.store._last_search_candidate_count, 500)
            entity = self.store.search_memories(
                1, "opportunity 41 backend", kind="semantic", limit=8
            )
            self.assertEqual(entity[0]["id"], entity_id)
            self.assertLessEqual(self.store._last_search_candidate_count, 500)

        with patch.object(
            self.store, "_fts_matches", side_effect=sqlite3.OperationalError("fallback")
        ):
            fallback = self.store.search_memories(
                1, "unique-needle-value", kind="semantic", limit=8
            )
        self.assertIn(needle_id, [row["id"] for row in fallback])
        self.assertLessEqual(self.store._last_search_candidate_count, 500)

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

    def test_snapshot_survives_blob_fields_and_keeps_healthy_rows(self):
        career = CareerService(self.db_path)
        healthy = career.create_opportunity(
            1, {"company": "Healthy Co", "job_title": "Engineer", "priority": 5}
        )
        career.create_action_item(1, {"title": "Healthy action", "type": "follow_up"})
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO job_applications
                    (user_id,company,job_title,status,updated_at,deleted_at)
                VALUES (1,?,?,?, ?,NULL)
                """,
                (sqlite3.Binary(b"\xffbad"), sqlite3.Binary(b"\xfetitle"), "已投递", sqlite3.Binary(b"\xffdate")),
            )
            conn.execute(
                "INSERT INTO resumes (user_id,title,content,status,updated_at) VALUES (1,?,'x','draft',?)",
                (sqlite3.Binary(b"\xffresume"), sqlite3.Binary(b"\xffdate")),
            )
            conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status,updated_at) VALUES (1,?,'follow_up','pending',?)",
                (sqlite3.Binary(b"\xffaction"), sqlite3.Binary(b"\xffdate")),
            )
            conn.execute(
                "INSERT INTO domain_events (user_id,aggregate_type,aggregate_id,event_type,payload_json,occurred_at) "
                "VALUES (1,?,?,?, ?,?)",
                (sqlite3.Binary(b"\xffagg"), "1", sqlite3.Binary(b"\xffevent"), sqlite3.Binary(b"\xffjson"), sqlite3.Binary(b"\xffdate")),
            )
        conversation = self.store.create_conversation(1, "Corrupt")
        snapshot = ContextBuilder(self.store, self.db_path).build(
            1, conversation.id, f"Healthy Co opportunity {healthy['id']}"
        ).career_snapshot
        self.assertIn("Healthy Co", snapshot)
        self.assertIn("Healthy action", snapshot)
        self.assertLessEqual(len(snapshot), 8000)

    def test_snapshot_prefers_relevant_newer_non_archived_resume_and_only_active_actions(self):
        career = CareerService(self.db_path)
        with connect(self.db_path) as conn:
            old_id = conn.execute(
                "INSERT INTO resumes (user_id,title,content,status,updated_at) "
                "VALUES (1,'Old active','x','active','2025-01-01T00:00:00+00:00')"
            ).lastrowid
            newer_id = conn.execute(
                "INSERT INTO resumes (user_id,title,content,status,parent_resume_id,updated_at) "
                "VALUES (1,'New tailored','x','draft',?,'2026-01-01T00:00:00+00:00')",
                (old_id,),
            ).lastrowid
            conn.execute(
                "INSERT INTO resumes (user_id,title,content,status,updated_at) "
                "VALUES (1,'Newest archived','x','archived','2027-01-01T00:00:00+00:00')"
            )
        opportunity = career.create_opportunity(
            1, {"company": "Relevant Co", "job_title": "Backend", "resume_id": newer_id}
        )
        active = career.create_action_item(1, {"title": "Active task", "type": "follow_up"})
        completed = career.create_action_item(1, {"title": "Completed task", "type": "follow_up"})
        career.complete_action_item(1, completed["id"])
        cancelled = career.create_action_item(
            1, {"title": "Cancelled task", "type": "follow_up", "status": "cancelled"}
        )
        conversation = self.store.create_conversation(1, "Selection")

        snapshot = ContextBuilder(self.store, self.db_path).build(
            1, conversation.id, f"Relevant Co opportunity {opportunity['id']}"
        ).career_snapshot

        self.assertIn('"title":"New tailored"', snapshot)
        self.assertNotIn("Old active", snapshot)
        self.assertNotIn("Newest archived", snapshot)
        self.assertIn("Active task", snapshot)
        self.assertNotIn("Completed task", snapshot)
        self.assertNotIn("Cancelled task", snapshot)
        self.assertIn(str(active["id"]), snapshot)
        self.assertNotIn(str(cancelled["id"]), snapshot.split("action_items:", 1)[1].splitlines()[0])

    def test_event_mapper_completes_only_exact_linked_actions_and_is_idempotent(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        exact = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Version", "type": "resume_version"}
        )
        wrong = career.create_action_item(1, {"title": "Unlinked", "type": "resume_version"})
        duplicate = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Other version", "type": "resume_version"}
        )
        generic = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Generic", "type": "follow_up"}
        )
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            apply_event_to_actions(
                conn, 1, "resume.version_created", "opportunity", opportunity["id"],
                {"resume_id": 7, "action_id": exact["id"]}
            )
            apply_event_to_actions(
                conn, 1, "resume.version_created", "opportunity", opportunity["id"],
                {"resume_id": 7, "action_id": exact["id"]}
            )
        rows = {row["id"]: row for row in career.list_action_items(1)}
        self.assertEqual(rows[exact["id"]]["status"], "completed")
        self.assertEqual(rows[wrong["id"]]["status"], "pending")
        self.assertEqual(rows[duplicate["id"]]["status"], "pending")
        self.assertEqual(rows[generic["id"]]["status"], "pending")
        self.assertIn("resume.version_created", rows[exact["id"]]["completion_evidence"])
        self.assertEqual(rows[exact["id"]]["source"], "domain_event")

    def test_event_mapper_rejects_wrong_aggregate_types_for_every_mapping(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        resume_action = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Resume", "type": "resume_version"}
        )
        interview_action = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Interview", "type": "interview_plan"}
        )
        report_action = career.create_action_item(
            1, {"title": "Report", "type": "career_report"}
        )
        with connect(self.db_path) as conn:
            session_id = conn.execute(
                "INSERT INTO interview_sessions (user_id,application_id,job_title) VALUES (1,?,'Engineer')",
                (opportunity["id"],),
            ).lastrowid
            apply_event_to_actions(
                conn, 1, "resume.version_created", "interview_session", opportunity["id"],
                {"resume_id": 7},
            )
            apply_event_to_actions(
                conn, 1, "interview.completed", "opportunity", session_id, {"score": 80}
            )
            apply_event_to_actions(
                conn, 1, "career_report.saved", "opportunity", 9,
                {"action_id": report_action["id"]},
            )
        statuses = {row["id"]: row["status"] for row in career.list_action_items(1)}
        self.assertEqual(statuses[resume_action["id"]], "pending")
        self.assertEqual(statuses[interview_action["id"]], "pending")
        self.assertEqual(statuses[report_action["id"]], "pending")

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
                    1, source_resume, "tailored",
                    {"application_id": opportunity["id"], "action_id": action["id"]}
                )
        self.assertEqual(career.list_action_items(1)[0]["status"], "pending")
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='resume.version_created'").fetchone()[0],
                0,
            )
        career.create_resume_version(
            1, source_resume, "tailored",
            {"application_id": opportunity["id"], "action_id": action["id"]}
        )
        conversation = self.store.create_conversation(1, "After event")
        snapshot = ContextBuilder(self.store, self.db_path).build(1, conversation.id, "actions").career_snapshot
        self.assertNotIn("Create tailored resume", snapshot)
        self.assertIn("resume.version_created", snapshot)
        self.assertEqual(career.list_action_items(1)[0]["id"], action["id"])

    def test_interview_and_report_writers_complete_only_their_action_types(self):
        career = CareerService(self.db_path)
        opportunity = career.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        interview_action = career.create_action_item(
            1, {"opportunity_id": opportunity["id"], "title": "Mock", "type": "mock_interview"}
        )
        report_action = career.create_action_item(1, {"title": "Save report", "type": "career_report"})
        wrong_report_action = career.create_action_item(
            1, {"title": "Other report", "type": "save_career_report"}
        )
        wrong_type_action = career.create_action_item(
            1, {"title": "Not a report", "type": "follow_up"}
        )
        completed_report_action = career.create_action_item(
            1, {"title": "Old report", "type": "career_report"}
        )
        career.complete_action_item(1, completed_report_action["id"])
        started_report_action = career.create_action_item(
            1, {"title": "Started report", "type": "career_report", "status": "in_progress"}
        )
        with connect(self.db_path) as conn:
            foreign_action_id = conn.execute(
                "INSERT INTO action_items (user_id,title,action_type,status) "
                "VALUES (2,'Foreign report','career_report','pending')"
            ).lastrowid
            apply_event_to_actions(
                conn, 1, "career_report.saved", "career_report", 99,
                {"action_id": started_report_action["id"]},
            )
            self.assertEqual(
                conn.execute(
                    "SELECT status FROM action_items WHERE id = ?",
                    (started_report_action["id"],),
                ).fetchone()[0],
                "in_progress",
            )
        with connect(self.db_path) as conn:
            session_id = conn.execute(
                "INSERT INTO interview_sessions (user_id,application_id,job_title) VALUES (1,?,'Engineer')",
                (opportunity["id"],),
            ).lastrowid
            InterviewService(self.db_path)._write_event(
                conn, session_id, "interview.completed",
                {"score": 77, "action_id": interview_action["id"]}
            )
        statuses = {row["id"]: row["status"] for row in career.list_action_items(1)}
        self.assertEqual(statuses[interview_action["id"]], "completed")
        self.assertEqual(statuses[report_action["id"]], "pending")

        career.save_report(
            1, {"report_type": "weekly", "title": "Unlinked", "content": {"score": 77}}
        )
        statuses = {row["id"]: row["status"] for row in career.list_action_items(1)}
        self.assertEqual(statuses[report_action["id"]], "pending")
        self.assertEqual(statuses[wrong_report_action["id"]], "pending")
        for invalid_action_id in (
            wrong_type_action["id"], completed_report_action["id"], foreign_action_id,
            started_report_action["id"],
        ):
            with self.subTest(action_id=invalid_action_id), self.assertRaises((LookupError, ValueError)):
                career.save_report(
                    1,
                    {
                        "report_type": "weekly", "content": {},
                        "action_id": invalid_action_id,
                    },
                )

        career.save_report(
            1,
            {
                "report_type": "weekly", "title": "Linked", "content": {"score": 77},
                "action_id": report_action["id"],
            },
        )
        rows = {row["id"]: row for row in career.list_action_items(1)}
        self.assertEqual(rows[report_action["id"]]["status"], "completed")
        self.assertEqual(rows[wrong_report_action["id"]]["status"], "pending")


if __name__ == "__main__":
    unittest.main()

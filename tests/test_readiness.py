import json
import os
import tempfile
import unittest
from unittest.mock import patch

from utils.domain.career import CareerService
from utils.domain.database import APPLICATION_STATUSES, connect, migrate_database


def create_readiness_database(db_path):
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                analysis_result TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                job_title TEXT NOT NULL,
                match_score INTEGER,
                analysis TEXT,
                jd_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resume_id INTEGER,
                job_title TEXT NOT NULL,
                conversation TEXT,
                score INTEGER,
                feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE practice_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT,
                question TEXT NOT NULL,
                answer TEXT,
                score INTEGER,
                feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE audio_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transcript TEXT NOT NULL,
                score INTEGER,
                metrics TEXT,
                feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                status TEXT,
                jd_text TEXT,
                next_action_at TEXT,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            """
        )
    migrate_database(db_path)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "readiness.db")
        create_readiness_database(self.db_path)
        self.service = CareerService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def insert(self, sql, values=()):
        with connect(self.db_path) as conn:
            return conn.execute(sql, values).lastrowid

    def add_resume(self, score=90):
        return self.insert(
            """INSERT INTO resumes (user_id, title, content, analysis_result, status)
               VALUES (1, 'Main', ?, ?, 'active')""",
            (
                "Summary\nPython engineer\nExperience\nBuilt APIs with measurable results\n"
                "Education\nSkills Python SQL testing",
                json.dumps({"score": score, "completeness": score}),
            ),
        )

    def add_match(self, resume_id, score=88, jd=True):
        return self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, jd_text)
               VALUES (1, ?, 'Backend Engineer', ?, ?, ?)""",
            (
                resume_id,
                score,
                json.dumps({"matched": ["Python", "SQL"]}),
                "Backend engineer requiring Python, SQL, APIs and testing." if jd else None,
            ),
        )

    def test_empty_user_has_stable_schema_and_low_score(self):
        result = self.service.calculate_readiness(1)

        self.assertLess(result["score"], 30)
        self.assertEqual(result["label"], "先补基础")
        self.assertEqual(set(result["components"]), {"resume", "alignment", "interview", "practice", "pipeline"})
        self.assertEqual(
            [result["components"][name]["weight"] for name in result["components"]],
            [25, 20, 25, 15, 15],
        )
        self.assertTrue(result["blockers"])
        self.assertTrue(result["weekly_plan"])

    def test_no_resume_caps_total_at_30(self):
        self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', 100)")
        self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', 100)")
        self.insert("INSERT INTO audio_records (user_id, transcript, score) VALUES (1, 'clear answer', 100)")
        self.insert(
            "INSERT INTO job_applications (user_id, company, job_title, status, jd_text, next_action_at) VALUES (1, 'A', 'Role', ?, 'real jd requirements', datetime('now', '+2 days'))",
            (APPLICATION_STATUSES[4],),
        )

        result = self.service.calculate_readiness(1)

        self.assertLessEqual(result["score"], 30)
        self.assertIn("no_resume", result["caps"])
        self.assertNotEqual(result["label"], "可投递")

    def test_resume_without_real_jd_caps_total_at_55(self):
        resume_id = self.add_resume()
        self.add_match(resume_id, score=99, jd=False)
        self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', 95)")
        self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', 95)")

        result = self.service.calculate_readiness(1)

        self.assertLessEqual(result["score"], 55)
        self.assertIn("no_real_jd_match", result["caps"])

    def test_repeated_zero_and_invalid_scores_do_not_create_positive_quality(self):
        resume_id = self.add_resume(score=20)
        for score in (0, 0, None, -1, 101):
            self.add_match(resume_id, score=score, jd=True)
            self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', ?)", (score,))
            self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', ?)", (score,))

        result = self.service.calculate_readiness(1)

        self.assertLess(result["score"], 35)
        self.assertLessEqual(result["components"]["alignment"]["score"], 5)
        self.assertLessEqual(result["components"]["interview"]["score"], 5)
        self.assertLessEqual(result["components"]["practice"]["score"], 5)

    def test_recent_low_interview_average_blocks_deliverable_label(self):
        resume_id = self.add_resume()
        self.add_match(resume_id)
        for score in (35, 38, 39):
            self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', ?)", (score,))
        self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', 95)")
        self.insert("INSERT INTO audio_records (user_id, transcript, score) VALUES (1, 'answer', 95)")
        self.insert(
            "INSERT INTO job_applications (user_id, company, job_title, status, jd_text, next_action_at) VALUES (1, 'A', 'Role', ?, 'real jd text', datetime('now', '+2 days'))",
            (APPLICATION_STATUSES[5],),
        )

        result = self.service.calculate_readiness(1)

        self.assertNotEqual(result["label"], "可投递")
        self.assertTrue(any("40" in blocker for blocker in result["blockers"]))

    def test_strong_end_to_end_evidence_reaches_deliverable(self):
        resume_id = self.add_resume(94)
        self.add_match(resume_id, 92)
        self.add_match(resume_id, 95)
        for score in (86, 90, 94):
            self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', ?)", (score,))
        for score in (82, 88, 93):
            self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', ?)", (score,))
        self.insert("INSERT INTO audio_records (user_id, transcript, score) VALUES (1, 'clear answer', 91)")
        for status in (APPLICATION_STATUSES[2], APPLICATION_STATUSES[4], APPLICATION_STATUSES[6]):
            self.insert(
                "INSERT INTO job_applications (user_id, company, job_title, status, jd_text, next_action_at) VALUES (1, 'A', 'Role', ?, 'real jd requirements', datetime('now', '+2 days'))",
                (status,),
            )

        result = self.service.calculate_readiness(1)

        self.assertGreaterEqual(result["score"], 70)
        self.assertEqual(result["label"], "可投递")
        self.assertEqual(result["caps"], [])

    def test_soft_deleted_opportunity_is_absent_from_pipeline_and_funnel(self):
        self.insert(
            "INSERT INTO job_applications (user_id, company, job_title, status, deleted_at) VALUES (1, 'Deleted', 'Role', ?, CURRENT_TIMESTAMP)",
            (APPLICATION_STATUSES[4],),
        )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["components"]["pipeline"]["score"], 0)
        self.assertEqual(result["funnel"], {})
        self.assertNotIn("Deleted", json.dumps(result, ensure_ascii=False))

    def test_component_evidence_is_concise_and_timestamped(self):
        resume_id = self.add_resume()
        self.add_match(resume_id)

        result = self.service.calculate_readiness(1)

        resume_evidence = result["components"]["resume"]["evidence"][0]
        match_evidence = result["components"]["alignment"]["evidence"][0]
        self.assertEqual(resume_evidence["entity_id"], resume_id)
        self.assertTrue(resume_evidence["timestamp"])
        self.assertTrue(match_evidence["timestamp"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("Built APIs with measurable results", serialized)
        self.assertNotIn("Backend engineer requiring Python", serialized)

    def test_rejects_non_local_user_and_is_deterministic(self):
        with self.assertRaisesRegex(PermissionError, "local user"):
            self.service.calculate_readiness(2)

        self.add_resume()
        self.assertEqual(self.service.calculate_readiness(1), self.service.calculate_readiness(1))


class DashboardReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "app.db")
        import app as app_module

        self.app_module = app_module
        self.old_db_path = app_module.DB_PATH
        app_module.DB_PATH = self.db_path
        app_module.init_db()
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.app_module.DB_PATH = self.old_db_path
        self.temp_dir.cleanup()

    def test_dashboard_uses_readiness_service_and_preserves_shapes(self):
        with patch.object(
            CareerService,
            "calculate_readiness",
            return_value={"score": 17, "label": "先补基础", "components": {}, "caps": [], "blockers": [], "weekly_plan": [], "summary": "service", "funnel": {}},
        ) as calculate:
            response = self.client.get("/api/dashboard/1")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        calculate.assert_called_once_with(1)
        self.assertEqual(data["career_pulse"]["summary"], "service")
        for key in ("stats", "interview_scores", "match_scores", "activities", "next_actions"):
            self.assertIn(key, data)

    def test_dashboard_rejects_non_local_user(self):
        response = self.client.get("/api/dashboard/2")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

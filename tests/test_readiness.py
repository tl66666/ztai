import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.agent_api_client import create_agent_test_runtime
from utils.domain.career import (
    DELIVERABLE_THRESHOLD,
    MIN_MEANINGFUL_JD_LENGTH,
    POLISH_THRESHOLD,
    CareerService,
    is_meaningful_jd_snapshot,
)
from utils.domain.database import APPLICATION_STATUSES, connect, migrate_database


def meaningful_jd(length=MIN_MEANINGFUL_JD_LENGTH):
    text = (
        "岗位职责：负责后端服务和数据接口设计开发。"
        "任职要求：熟悉 Python、SQL、API 和自动化测试技能。"
        "参与系统架构、性能优化、测试与上线维护，具备团队协作、问题分析与持续交付经验。"
    )
    text += "候选人需要能够根据业务目标持续改进服务质量和可靠性。" * 5
    return text[:length]


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
                audio_file TEXT,
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
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "readiness.db")
        create_readiness_database(self.db_path)
        self.service = CareerService(self.db_path)

    def tearDown(self):
        import gc, shutil
        gc.collect()
        try:
            import gc, shutil
            gc.collect()
            try:
                self.temp_dir.cleanup()
            except (PermissionError, OSError):
                shutil.rmtree(self.temp_dir.name, ignore_errors=True)
        except (PermissionError, OSError):
            shutil.rmtree(self.temp_dir.name, ignore_errors=True)
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
                meaningful_jd() if jd else None,
            ),
        )

    def seed_complete_evidence(self):
        timestamp = "2026-07-01 00:00:00"
        resume_id = self.add_resume(94)
        with connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO job_matches
                   (user_id, resume_id, job_title, match_score, analysis, jd_text, created_at)
                   VALUES (1, ?, 'Backend Engineer', 92, '{}', ?, ?)""",
                (resume_id, meaningful_jd(), timestamp),
            )
            conn.execute(
                "INSERT INTO interviews (user_id, job_title, score, created_at) VALUES (1, 'Role', 88, ?)",
                (timestamp,),
            )
            conn.execute(
                "INSERT INTO practice_records (user_id, category, question, answer, score, created_at) VALUES (1, 'python', 'Q', 'same answer', 86, ?)",
                (timestamp,),
            )
            conn.execute(
                "INSERT INTO audio_records (user_id, transcript, metrics, score, created_at) VALUES (1, 'answer', '{}', 90, ?)",
                (timestamp,),
            )
            conn.execute(
                """INSERT INTO job_applications
                   (user_id, company, job_title, status, jd_text, next_action_at, updated_at)
                   VALUES (1, 'A', 'Role', ?, 'real jd requirements', datetime('now', '+2 days'), ?)""",
                (APPLICATION_STATUSES[6], timestamp),
            )
        return resume_id, timestamp

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
        self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, jd_text)
               VALUES (1, 999, 'Role', 100, '{}', ?)""",
            (meaningful_jd(),),
        )
        self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', 100)")
        self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', 100)")
        self.insert("INSERT INTO audio_records (user_id, transcript, score) VALUES (1, 'clear answer', 100)")
        self.insert(
            "INSERT INTO job_applications (user_id, company, job_title, status, jd_text, next_action_at) VALUES (1, 'A', 'Role', ?, 'real jd requirements', datetime('now', '+2 days'))",
            (APPLICATION_STATUSES[4],),
        )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["score"], 30)
        self.assertIn("no_resume", result["caps"])
        self.assertNotEqual(result["label"], "可投递")

    def test_resume_without_real_jd_caps_total_at_55(self):
        resume_id = self.add_resume()
        self.add_match(resume_id, score=99, jd=False)
        self.insert("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', 95)")
        self.insert("INSERT INTO practice_records (user_id, question, score) VALUES (1, 'Q', 95)")

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["score"], 55)
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

    def test_duplicate_match_does_not_inflate_component_or_final_score(self):
        resume_id, timestamp = self.seed_complete_evidence()
        self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, jd_text, created_at)
               VALUES (1, ?, 'Backend Engineer', 70, '{}', ?, '2026-06-30 00:00:00')""",
            (resume_id, meaningful_jd()),
        )
        before = self.service.calculate_readiness(1)

        for day in range(2, 7):
            self.insert(
                """INSERT INTO job_matches
                   (user_id, resume_id, job_title, match_score, analysis, jd_text, created_at)
                   VALUES (1, ?, 'Backend Engineer', 92, '{}', ?, ?)""",
                (resume_id, meaningful_jd(), f"2026-07-{day:02d} 00:00:00"),
            )
        after = self.service.calculate_readiness(1)

        self.assertEqual(after["components"]["alignment"]["score"], before["components"]["alignment"]["score"])
        self.assertEqual(after["score"], before["score"])

    def test_duplicate_interview_does_not_inflate_component_or_final_score(self):
        _, timestamp = self.seed_complete_evidence()
        self.insert(
            "INSERT INTO interviews (user_id, job_title, score, created_at) VALUES (1, 'Role', 60, '2026-06-30 00:00:00')"
        )
        before = self.service.calculate_readiness(1)

        for day in range(2, 7):
            self.insert(
                "INSERT INTO interviews (user_id, job_title, score, created_at) VALUES (1, 'Role', 88, ?)",
                (f"2026-07-{day:02d} 00:00:00",),
            )
        after = self.service.calculate_readiness(1)

        self.assertEqual(after["components"]["interview"]["score"], before["components"]["interview"]["score"])
        self.assertEqual(after["score"], before["score"])

    def test_duplicate_practice_and_audio_do_not_inflate_component_or_final_score(self):
        _, timestamp = self.seed_complete_evidence()
        self.insert(
            "INSERT INTO practice_records (user_id, question, score, created_at) VALUES (1, 'Q', 60, '2026-06-30 00:00:00')"
        )
        self.insert(
            "INSERT INTO audio_records (user_id, transcript, score, created_at) VALUES (1, 'answer', 70, '2026-06-30 00:00:00')"
        )
        before = self.service.calculate_readiness(1)

        for day in range(2, 7):
            created_at = f"2026-07-{day:02d} 00:00:00"
            self.insert(
                "INSERT INTO practice_records (user_id, category, question, answer, score, created_at) VALUES (1, 'python', 'Q', 'same answer', 86, ?)",
                (created_at,),
            )
            self.insert(
                "INSERT INTO audio_records (user_id, transcript, metrics, score, created_at) VALUES (1, 'answer', '{}', 90, ?)",
                (created_at,),
            )
        after = self.service.calculate_readiness(1)

        self.assertEqual(after["components"]["practice"]["score"], before["components"]["practice"]["score"])
        self.assertEqual(after["score"], before["score"])

    def test_label_thresholds_are_exact_and_caps_override_deliverable(self):
        self.assertEqual(CareerService._readiness_label(POLISH_THRESHOLD - 1, [], False), "先补基础")
        self.assertEqual(CareerService._readiness_label(POLISH_THRESHOLD, [], False), "需要打磨")
        self.assertEqual(CareerService._readiness_label(DELIVERABLE_THRESHOLD - 1, [], False), "需要打磨")
        self.assertEqual(CareerService._readiness_label(DELIVERABLE_THRESHOLD, [], False), "可投递")
        self.assertEqual(CareerService._readiness_label(100, ["no_resume"], False), "需要打磨")
        self.assertEqual(CareerService._readiness_label(100, [], True), "需要打磨")

    def test_interview_average_boundary_is_39_blocked_and_40_allowed(self):
        self.seed_complete_evidence()
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM interviews")
            conn.execute("INSERT INTO interviews (user_id, job_title, score) VALUES (1, 'Role', 39)")
        below = self.service.calculate_readiness(1)
        with connect(self.db_path) as conn:
            conn.execute("UPDATE interviews SET score = 40")
        at_boundary = self.service.calculate_readiness(1)

        self.assertTrue(any("40" in blocker for blocker in below["blockers"]))
        self.assertFalse(any("40" in blocker for blocker in at_boundary["blockers"]))
        self.assertNotEqual(below["label"], "可投递")

    def test_real_jd_length_boundary_is_exact(self):
        self.assertFalse(is_meaningful_jd_snapshot(meaningful_jd(MIN_MEANINGFUL_JD_LENGTH - 1)))
        self.assertTrue(is_meaningful_jd_snapshot(meaningful_jd(MIN_MEANINGFUL_JD_LENGTH)))
        self.assertFalse(is_meaningful_jd_snapshot("岗位职责任职要求技能" + "J" * 200))

    def test_recency_cutoffs_are_exact(self):
        now = datetime.now(timezone.utc)
        cases = (
            (30, 1.0),
            (31, 0.85),
            (90, 0.85),
            (91, 0.70),
            (180, 0.70),
            (181, 0.55),
        )
        for days, expected in cases:
            with self.subTest(days=days):
                timestamp = (now - timedelta(days=days, minutes=1)).isoformat()
                self.assertEqual(CareerService._recency_factor(timestamp), expected)

    def test_valid_score_endpoints_and_invalid_values(self):
        self.assertTrue(CareerService._valid_score(0))
        self.assertTrue(CareerService._valid_score(100))
        for value in (-1, 101, None):
            with self.subTest(value=value):
                self.assertFalse(CareerService._valid_score(value))

    def test_soft_deleted_application_linked_match_is_excluded(self):
        resume_id = self.add_resume()
        application_id = self.insert(
            """INSERT INTO job_applications
               (user_id, company, job_title, status, jd_text, deleted_at)
               VALUES (1, 'Deleted', 'Role', ?, ?, CURRENT_TIMESTAMP)""",
            (APPLICATION_STATUSES[3], meaningful_jd()),
        )
        self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, jd_text, application_id)
               VALUES (1, ?, 'Role', 100, '{}', ?, ?)""",
            (resume_id, meaningful_jd(), application_id),
        )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["components"]["alignment"]["score"], 0)
        self.assertIn("no_real_jd_match", result["caps"])

    def test_cross_user_application_cannot_supply_match_jd(self):
        resume_id = self.add_resume()
        application_id = self.insert(
            """INSERT INTO job_applications
               (user_id, company, job_title, status, jd_text)
               VALUES (2, 'Private', 'Role', ?, ?)""",
            (APPLICATION_STATUSES[3], meaningful_jd()),
        )
        self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, application_id)
               VALUES (1, ?, 'Role', 100, '{}', ?)""",
            (resume_id, application_id),
        )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["components"]["alignment"]["score"], 0)
        self.assertIn("no_real_jd_match", result["caps"])

    def test_direct_match_requires_an_owned_resume(self):
        other_resume = self.insert(
            "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Private', 'secret')"
        )
        self.insert(
            """INSERT INTO job_matches
               (user_id, resume_id, job_title, match_score, analysis, jd_text)
               VALUES (1, ?, 'Role', 100, '{}', ?)""",
            (other_resume, meaningful_jd()),
        )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["components"]["alignment"]["score"], 0)
        self.assertIn("no_real_jd_match", result["caps"])

    def test_duplicate_low_interview_identity_does_not_escape_blocker(self):
        self.seed_complete_evidence()
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM interviews")
            for day in range(1, 7):
                conn.execute(
                    """INSERT INTO interviews
                       (user_id, job_title, conversation, source_session_id, score, created_at)
                       VALUES (1, 'Role', '[{\"answer\":\"same\"}]', 'session-low', 39, datetime('now', ?))""",
                    (f"-{day} days",),
                )

        result = self.service.calculate_readiness(1)

        self.assertEqual(result["components"]["interview"]["score"], 39)
        self.assertTrue(any("40" in blocker for blocker in result["blockers"]))
        self.assertNotEqual(result["label"], "可投递")

    def test_mixed_offset_timestamps_sort_by_utc_instant(self):
        rows = [
            {"id": 1, "created_at": "2026-07-01T10:00:00+08:00"},
            {"id": 2, "created_at": "2026-07-01T03:00:00+00:00"},
            {"id": 3, "created_at": "2026-07-01 01:00:00"},
        ]

        ordered = CareerService._sort_recent_rows(rows)

        self.assertEqual([row["id"] for row in ordered], [2, 1, 3])


class DashboardReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "app.db")
        self.client_context, self.client = create_agent_test_runtime(
            self.temp_dir.name,
            db_name="app.db",
        )
        self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        import gc, shutil
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temp_dir.name, ignore_errors=True)
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

    def test_job_match_persists_evidence_and_clears_readiness_cap(self):
        with connect(self.db_path) as conn:
            resume_id = conn.execute(
                """INSERT INTO resumes (user_id, title, content, analysis_result)
                   VALUES (1, 'Main', 'Python SQL API testing backend services', '{\"score\": 90}')"""
            ).lastrowid
            application_id = conn.execute(
                """INSERT INTO job_applications
                   (user_id, company, job_title, status, jd_text)
                   VALUES (1, 'Acme', 'Backend Engineer', ?, ?)""",
                (APPLICATION_STATUSES[1], meaningful_jd()),
            ).lastrowid

        response = self.client.post(
            "/api/job-match",
            json={
                "resume_id": resume_id,
                "application_id": application_id,
                "job_title": "Backend Engineer",
                "jd": meaningful_jd(),
            },
        )
        readiness = CareerService(self.db_path).calculate_readiness(1)
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM job_matches ORDER BY id DESC LIMIT 1").fetchone()
            details = json.loads(row["details_json"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(row["user_id"], 1)
        self.assertEqual(row["resume_id"], resume_id)
        self.assertEqual(row["application_id"], application_id)
        self.assertEqual(row["jd_text"], meaningful_jd())
        self.assertIn("matched", details)
        self.assertIn("missing", details)
        self.assertIn("provider", details)
        self.assertNotIn("no_real_jd_match", readiness["caps"])
        self.assertGreater(readiness["components"]["alignment"]["score"], 0)

    def test_job_match_rejects_invalid_and_cross_user_resume(self):
        with connect(self.db_path) as conn:
            other_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Private', 'secret')"
            ).lastrowid

        invalid = self.client.post(
            "/api/job-match", json={"resume_id": "not-an-id", "jd": meaningful_jd()}
        )
        cross_user = self.client.post(
            "/api/job-match", json={"resume_id": other_resume, "jd": meaningful_jd()}
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(cross_user.status_code, 404)


if __name__ == "__main__":
    unittest.main()

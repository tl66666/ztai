import json
import importlib
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from utils.domain.database import connect, migrate_database

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def create_database(db_path):
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE TABLE job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                status TEXT,
                deleted_at TEXT
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
            """
        )
    migrate_database(db_path)


def stages(_session):
    return [
        ("resume_deep_dive", "Resume question"),
        ("professional", "Professional question"),
        ("behavioral", "Behavioral question"),
        ("candidate_questions", "Candidate question"),
        ("finished", "Interview finished"),
    ]


def evaluate(_session, answer, duration_seconds, stage):
    skipped = answer.lower() in {"skip", "pass"}
    score = 0 if skipped else 80
    voice = {"overall_score": score, "tips": [], "duration_seconds": duration_seconds}
    return (
        {"role": "candidate", "content": answer, "voice": voice},
        {"score": score, "summary": "Skipped" if skipped else f"Feedback for {stage}", "voice": voice},
        skipped,
    )


class InterviewPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "interviews.db")
        create_database(self.db_path)
        with connect(self.db_path) as conn:
            self.resume_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Resume', 'Python projects')"
            ).lastrowid
        self.service = self.make_service()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_service(self, local_user_id=1):
        from utils.domain.interviews import InterviewService

        return InterviewService(
            self.db_path,
            local_user_id=local_user_id,
            stages_builder=stages,
            answer_evaluator=evaluate,
            profile_resolver=lambda profile: {
                "id": profile or "tech",
                "label": "Technology",
                "interviewer": "Technical interviewer",
            },
        )

    def start(self, **overrides):
        values = {
            "user_id": 1,
            "resume_id": self.resume_id,
            "job_title": "Backend Engineer",
            "jd": "Build APIs",
            "mode": "standard",
            "career_profile": "tech",
        }
        values.update(overrides)
        return self.service.start(**values)

    def test_start_then_new_service_resumes_complete_state(self):
        started = self.start()

        resumed = self.make_service().get(1, started["session_id"])

        self.assertEqual(resumed["session_id"], started["session_id"])
        self.assertEqual(resumed["stage"], "opening")
        self.assertEqual(resumed["question"], started["question"])
        self.assertEqual(resumed["progress"], 1)
        self.assertEqual(resumed["total"], 6)
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT conversation_json, current_stage, status FROM interview_sessions WHERE id = ?",
                (started["session_id"],),
            ).fetchone()
        state = json.loads(row["conversation_json"])
        self.assertEqual(row["current_stage"], "opening")
        self.assertEqual(row["status"], "active")
        self.assertEqual(state["jd"], "Build APIs")
        self.assertEqual(state["career_profile"], "tech")
        self.assertEqual(state["stage_index"], 0)
        self.assertIsInstance(started["session_id"], str)
        self.assertIsInstance(resumed["session_id"], str)

    def test_concurrent_duplicate_submission_advances_once(self):
        session_id = self.start()["session_id"]
        barrier = threading.Barrier(2)

        def submit():
            barrier.wait()
            return self.make_service().answer(
                1,
                session_id,
                "The same answer",
                submission_id="submission-concurrent-1",
                expected_stage_index=0,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _index: submit(), range(2)))

        self.assertEqual([response["progress"] for response in responses], [2, 2])
        self.assertEqual(sum(bool(response.get("idempotent")) for response in responses), 1)
        with connect(self.db_path) as conn:
            state = json.loads(
                conn.execute(
                    "SELECT conversation_json FROM interview_sessions WHERE id = ?", (session_id,)
                ).fetchone()[0]
            )
            answered_events = conn.execute(
                """
                SELECT COUNT(*) FROM domain_events
                WHERE aggregate_id = ? AND event_type = 'interview.answered'
                """,
                (session_id,),
            ).fetchone()[0]
        candidates = [item for item in state["conversation"] if item["role"] == "candidate"]
        self.assertEqual(state["stage_index"], 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(answered_events, 1)

    def test_stale_expected_stage_conflicts_without_advancing(self):
        from utils.domain.interviews import InterviewConflictError

        session_id = self.start()["session_id"]
        self.service.answer(
            1,
            session_id,
            "First answer",
            submission_id="submission-first",
            expected_stage_index=0,
        )

        with self.assertRaises(InterviewConflictError):
            self.service.answer(
                1,
                session_id,
                "Stale second answer",
                submission_id="submission-stale",
                expected_stage_index=0,
            )

        self.assertEqual(self.service.get(1, session_id)["progress"], 2)

    def test_open_list_isolates_corrupt_session_state(self):
        healthy_id = self.start()["session_id"]
        with connect(self.db_path) as conn:
            malformed_id = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, job_title, status, current_stage, conversation_json
                ) VALUES (1, 'Malformed', 'active', 'opening', '{')
                """
            ).lastrowid
            non_object_id = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, job_title, status, current_stage, conversation_json
                ) VALUES (1, 'Non-object', 'active', 'opening', '[]')
                """
            ).lastrowid
            invalid_stage_id = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, job_title, status, current_stage, conversation_json
                ) VALUES (1, 'Invalid stage', 'active', 'opening', ?)
                """,
                (
                    json.dumps(
                        {
                            "version": 1,
                            "stage_index": 99,
                            "conversation": [],
                            "current_question": "Invalid",
                        }
                    ),
                ),
            ).lastrowid

        sessions = self.make_service().list_open(1)

        healthy = [item for item in sessions if item.get("status") == "active"]
        recovery = [item for item in sessions if item.get("status") == "recovery_error"]
        self.assertEqual([item["session_id"] for item in healthy], [healthy_id])
        self.assertEqual(
            {item["session_id"] for item in recovery},
            {str(malformed_id), str(non_object_id), str(invalid_stage_id)},
        )
        self.assertTrue(all(item["recovery_error"] == "invalid interview session state" for item in recovery))
        corrupt = self.make_service().get(1, malformed_id)
        self.assertEqual(corrupt["status"], "recovery_error")
        self.assertEqual(corrupt["session_id"], str(malformed_id))

    def test_poisoned_cached_submission_quarantines_session_and_cannot_replay(self):
        session_id = self.start()["session_id"]
        self.service.answer(
            1,
            session_id,
            "Original answer",
            submission_id="valid-submission",
            expected_stage_index=0,
        )
        with connect(self.db_path) as conn:
            state = json.loads(
                conn.execute(
                    "SELECT conversation_json FROM interview_sessions WHERE id = ?", (session_id,)
                ).fetchone()[0]
            )
            state["processed_submissions"] = {"poisoned-submission": {}}
            conn.execute(
                "UPDATE interview_sessions SET conversation_json = ? WHERE id = ?",
                (json.dumps(state), session_id),
            )

        recovered = self.make_service().get(1, session_id)
        listed = self.make_service().list_open(1)
        with self.assertRaisesRegex(ValueError, "invalid interview session state"):
            self.make_service().answer(
                1,
                session_id,
                "Poisoned retry",
                submission_id="poisoned-submission",
                expected_stage_index=1,
            )

        self.assertEqual(recovered["status"], "recovery_error")
        self.assertEqual(listed[0]["status"], "recovery_error")
        with connect(self.db_path) as conn:
            persisted = json.loads(
                conn.execute(
                    "SELECT conversation_json FROM interview_sessions WHERE id = ?", (session_id,)
                ).fetchone()[0]
            )
            answered_events = conn.execute(
                "SELECT COUNT(*) FROM domain_events WHERE event_type = 'interview.answered'"
            ).fetchone()[0]
        self.assertEqual(
            len([item for item in persisted["conversation"] if item["role"] == "candidate"]), 1
        )
        self.assertEqual(answered_events, 1)

    def test_answer_is_persisted_and_resumable(self):
        session_id = self.start()["session_id"]

        answered = self.service.answer(1, session_id, "A substantive answer", 42)
        resumed = self.make_service().get(1, session_id)

        self.assertEqual(answered["stage"], "resume_deep_dive")
        self.assertEqual(resumed["stage"], "resume_deep_dive")
        self.assertEqual(resumed["question"], "Resume question")
        self.assertEqual(resumed["progress"], 2)
        with connect(self.db_path) as conn:
            state = json.loads(
                conn.execute(
                    "SELECT conversation_json FROM interview_sessions WHERE id = ?", (session_id,)
                ).fetchone()[0]
            )
        self.assertEqual(state["conversation"][1]["content"], "A substantive answer")
        self.assertEqual(state["conversation"][1]["voice"]["duration_seconds"], 42)

    def test_completion_inserts_result_once_and_repeat_is_idempotent(self):
        session_id = self.start()["session_id"]
        for index in range(4):
            self.service.answer(1, session_id, f"Answer {index} with enough detail")

        completed = self.service.answer(1, session_id, "Final answer with enough detail")
        repeated = self.service.answer(1, session_id, "Retried final answer")

        self.assertEqual(completed["stage"], "finished")
        self.assertEqual(completed["question"], "Interview finished")
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(repeated["status"], "completed")
        with connect(self.db_path) as conn:
            result_count = conn.execute("SELECT COUNT(*) FROM interviews").fetchone()[0]
            completion_events = conn.execute(
                "SELECT COUNT(*) FROM domain_events WHERE event_type = 'interview.completed'"
            ).fetchone()[0]
        self.assertEqual(result_count, 1)
        self.assertEqual(completion_events, 1)

    def test_open_list_excludes_completed_sessions(self):
        open_id = self.start(job_title="Open role")["session_id"]
        completed_id = self.start(job_title="Completed role")["session_id"]
        for index in range(5):
            self.service.answer(1, completed_id, f"Answer {index} with enough detail")

        sessions = self.make_service().list_open(1)

        self.assertEqual([item["session_id"] for item in sessions], [open_id])

    def test_fixed_user_and_cross_user_resources_are_rejected(self):
        with connect(self.db_path) as conn:
            foreign_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Private', 'Secret')"
            ).lastrowid
            foreign_application = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (2, 'Private', 'Role')"
            ).lastrowid
        with self.assertRaises(PermissionError):
            self.start(user_id=2)
        with self.assertRaises(PermissionError):
            self.start(resume_id=foreign_resume)
        with self.assertRaises(PermissionError):
            self.start(application_id=foreign_application)

        session_id = self.start()["session_id"]
        with connect(self.db_path) as conn:
            conn.execute("UPDATE interview_sessions SET user_id = 2 WHERE id = ?", (session_id,))
        with self.assertRaises(PermissionError):
            self.service.get(1, session_id)
        with self.assertRaises(PermissionError):
            self.service.answer(1, session_id, "Answer")

    def test_deleted_or_archived_resources_are_rejected(self):
        with connect(self.db_path) as conn:
            archived_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content, status) VALUES (1, 'Old', 'Old', 'archived')"
            ).lastrowid
            deleted_application = conn.execute(
                """
                INSERT INTO job_applications (user_id, company, job_title, deleted_at)
                VALUES (1, 'Deleted', 'Role', CURRENT_TIMESTAMP)
                """
            ).lastrowid
        with self.assertRaises(LookupError):
            self.start(resume_id=archived_resume)
        with self.assertRaises(LookupError):
            self.start(application_id=deleted_application)

    def test_empty_answer_is_rejected_without_changing_state(self):
        session_id = self.start()["session_id"]
        with self.assertRaises(ValueError):
            self.service.answer(1, session_id, "   ")
        self.assertEqual(self.service.get(1, session_id)["progress"], 1)

    def test_skip_behavior_is_persisted_without_inflating_score(self):
        session_id = self.start()["session_id"]

        result = self.service.answer(1, session_id, "skip")

        self.assertEqual(result["feedback"]["score"], 0)
        self.assertEqual(self.make_service().get(1, session_id)["progress"], 2)
        with connect(self.db_path) as conn:
            payload = json.loads(
                conn.execute(
                    "SELECT payload_json FROM domain_events WHERE event_type = 'interview.answered'"
                ).fetchone()[0]
            )
        self.assertTrue(payload["skipped"])
        self.assertNotIn("answer", payload)


class InterviewApiPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "api.db")
        os.environ["JOBHUNTER_DB_PATH"] = self.db_path
        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.app_module.app.config["TESTING"] = True
        self.app_module.init_db()
        self.app_module._interview_service = None
        self.client = self.app_module.app.test_client()
        with connect(self.db_path) as conn:
            self.resume_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Resume', 'Python testing')"
            ).lastrowid

    def tearDown(self):
        self.app_module._interview_service = None
        self.temp_dir.cleanup()
        os.environ.pop("JOBHUNTER_DB_PATH", None)

    def start(self, **overrides):
        body = {
            "user_id": 2,
            "resume_id": self.resume_id,
            "job_title": "QA Engineer",
            "jd": "Test APIs",
            "mode": "campus",
        }
        body.update(overrides)
        return self.client.post("/api/interview/sessions", json=body)

    def test_flask_recreates_cached_service_and_continues_session(self):
        started_response = self.start()
        started = started_response.get_json()
        self.app_module._interview_service = None

        answered_response = self.client.post(
            f"/api/interview/sessions/{started['session_id']}/answer",
            json={"answer": "I tested a Flask application with API automation."},
        )
        open_response = self.client.get("/api/interview/sessions/open")

        self.assertEqual(started_response.status_code, 200)
        self.assertEqual(answered_response.status_code, 200)
        self.assertEqual(answered_response.get_json()["progress"], 2)
        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(open_response.get_json()["data"][0]["session_id"], started["session_id"])
        with connect(self.db_path) as conn:
            owner = conn.execute(
                "SELECT user_id FROM interview_sessions WHERE id = ?", (started["session_id"],)
            ).fetchone()[0]
        self.assertEqual(owner, 1)
        self.assertIsInstance(started["session_id"], str)

    def test_duplicate_api_submission_advances_once_and_stale_submission_conflicts(self):
        session_id = self.start().get_json()["session_id"]
        body = {
            "answer": "I tested the same API response.",
            "submission_id": "api-submission-1",
            "expected_stage_index": 0,
        }

        first = self.client.post(f"/api/interview/sessions/{session_id}/answer", json=body)
        duplicate = self.client.post(f"/api/interview/sessions/{session_id}/answer", json=body)
        conflict = self.client.post(
            f"/api/interview/sessions/{session_id}/answer",
            json={
                "answer": "A stale different answer",
                "submission_id": "api-submission-2",
                "expected_stage_index": 0,
            },
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.get_json()["idempotent"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["code"], "interview_stage_conflict")
        with connect(self.db_path) as conn:
            state = json.loads(
                conn.execute(
                    "SELECT conversation_json FROM interview_sessions WHERE id = ?", (session_id,)
                ).fetchone()[0]
            )
            answered_events = conn.execute(
                "SELECT COUNT(*) FROM domain_events WHERE event_type = 'interview.answered'"
            ).fetchone()[0]
        self.assertEqual(state["stage_index"], 1)
        self.assertEqual(
            len([item for item in state["conversation"] if item["role"] == "candidate"]), 1
        )
        self.assertEqual(answered_events, 1)

    def test_open_api_returns_healthy_and_recovery_items_for_corrupt_rows(self):
        healthy_id = self.start().get_json()["session_id"]
        with connect(self.db_path) as conn:
            corrupt_id = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, job_title, status, current_stage, conversation_json
                ) VALUES (1, 'Corrupt', 'active', 'opening', 'null')
                """
            ).lastrowid

        response = self.client.get("/api/interview/sessions/open")

        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        self.assertIn(healthy_id, [item["session_id"] for item in items])
        self.assertIn(
            {"session_id": str(corrupt_id), "status": "recovery_error", "recovery_error": "invalid interview session state"},
            items,
        )

    def test_get_session_returns_current_state_and_stable_missing_corrupt_errors(self):
        session_id = self.start().get_json()["session_id"]
        healthy = self.client.get(f"/api/interview/sessions/{session_id}")
        missing = self.client.get("/api/interview/sessions/99999")
        with connect(self.db_path) as conn:
            corrupt_id = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, job_title, status, current_stage, conversation_json
                ) VALUES (1, 'Corrupt', 'active', 'opening', '{}')
                """
            ).lastrowid
        corrupt = self.client.get(f"/api/interview/sessions/{corrupt_id}")

        self.assertEqual(healthy.status_code, 200)
        self.assertEqual(healthy.get_json()["session_id"], session_id)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["code"], "interview_session_not_found")
        self.assertEqual(corrupt.status_code, 409)
        self.assertEqual(corrupt.get_json()["code"], "interview_session_recovery_error")

    def test_non_object_json_and_empty_answers_return_stable_400(self):
        start_response = self.client.post("/api/interview/sessions", json=[])
        session_id = self.start().get_json()["session_id"]
        non_object_answer = self.client.post(
            f"/api/interview/sessions/{session_id}/answer", json=[]
        )
        empty_answer = self.client.post(
            f"/api/interview/sessions/{session_id}/answer", json={"answer": "   "}
        )

        self.assertEqual(start_response.status_code, 400)
        self.assertEqual(start_response.get_json()["message"], "JSON body must be an object")
        self.assertEqual(non_object_answer.status_code, 400)
        self.assertEqual(non_object_answer.get_json()["message"], "JSON body must be an object")
        self.assertEqual(empty_answer.status_code, 400)
        self.assertEqual(empty_answer.get_json()["message"], "answer is required")

    def test_submission_metadata_must_be_a_valid_complete_pair(self):
        invalid_bodies = [
            {"answer": "Answer", "submission_id": "", "expected_stage_index": 0},
            {"answer": "Answer", "submission_id": "submission-only"},
            {"answer": "Answer", "expected_stage_index": 0},
            {
                "answer": "Answer",
                "submission_id": "submission-string-stage",
                "expected_stage_index": "0",
            },
        ]

        for body in invalid_bodies:
            with self.subTest(body=body):
                session_id = self.start().get_json()["session_id"]
                response = self.client.post(
                    f"/api/interview/sessions/{session_id}/answer", json=body
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    self.app_module.get_interview_service().get(1, session_id)["progress"], 1
                )

        legacy_session_id = self.start().get_json()["session_id"]
        legacy = self.client.post(
            f"/api/interview/sessions/{legacy_session_id}/answer",
            json={"answer": "Legacy caller omits both metadata fields"},
        )
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.get_json()["progress"], 2)

    def test_missing_and_cross_user_sessions_return_404_and_403(self):
        missing = self.client.post(
            "/api/interview/sessions/99999/answer", json={"answer": "Answer"}
        )
        started = self.start().get_json()
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE interview_sessions SET user_id = 2 WHERE id = ?",
                (started["session_id"],),
            )
        cross_user = self.client.post(
            f"/api/interview/sessions/{started['session_id']}/answer",
            json={"answer": "Answer"},
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(cross_user.status_code, 403)


class InterviewFrontendSubmissionTests(unittest.TestCase):
    def test_frontend_sends_one_reusable_submission_identity_and_stage_precondition(self):
        with open(
            os.path.join(PROJECT_ROOT, "static", "js", "app.js"), encoding="utf-8"
        ) as file:
            script = file.read()

        self.assertIn("interviewStageIndex", script)
        self.assertIn("pendingInterviewSubmission", script)
        self.assertIn("interviewSubmitting", script)
        self.assertIn("crypto.randomUUID", script)
        self.assertIn("submission_id: pending.submissionId", script)
        self.assertIn("expected_stage_index: pending.expectedStageIndex", script)
        self.assertIn("if (state.interviewSubmitting) return", script)
        self.assertIn("http_status: response.status", script)
        with open(
            os.path.join(PROJECT_ROOT, "static", "index.html"), encoding="utf-8"
        ) as file:
            html = file.read()
        self.assertIn('<script src="js/interview_submission.js"></script>', html)


if __name__ == "__main__":
    unittest.main()

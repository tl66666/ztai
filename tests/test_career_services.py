import json
import os
import tempfile
import unittest
from unittest.mock import patch

from utils.domain.database import APPLICATION_STATUSES, connect, migrate_database


def create_database(db_path):
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,
                analysis_result TEXT,
                tailored_result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                status TEXT,
                city TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                notes TEXT,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                job_title TEXT NOT NULL
            );
            """
        )
    migrate_database(db_path)


class CareerServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "career.db")
        create_database(self.db_path)
        from utils.domain.career import CareerService

        self.service = CareerService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_profile_upsert_round_trips_canonical_fields(self):
        values = {
            "career_direction": "software",
            "target_role": "Backend Engineer",
            "cities": ["Shanghai", "Hangzhou"],
            "salary": {"min": 20, "max": 30},
            "experience": "Three years in Python services",
            "confirmed_skills": ["Python", "SQL"],
            "preferences": {"remote": True},
            "constraints": ["No relocation"],
            "source_metadata": {"form": "onboarding"},
        }

        profile = self.service.upsert_profile(1, values)

        self.assertEqual(self.service.get_profile(1), profile)
        self.assertEqual(profile["target_role"], "Backend Engineer")
        self.assertEqual(profile["confirmed_skills"], ["Python", "SQL"])
        self.assertEqual(profile["source_metadata"]["source"], "user")

    def test_every_public_method_rejects_non_local_user(self):
        calls = [
            lambda: self.service.get_profile(2),
            lambda: self.service.upsert_profile(2, {}),
            lambda: self.service.list_opportunities(2),
            lambda: self.service.get_opportunity(2, 1),
            lambda: self.service.create_opportunity(2, {"company": "A", "job_title": "B"}),
            lambda: self.service.update_opportunity(2, 1, {}),
            lambda: self.service.create_resume_version(2, 1, "content", {}),
            lambda: self.service.create_action_item(2, {"title": "Follow up"}),
            lambda: self.service.complete_action_item(2, 1),
            lambda: self.service.timeline(2, 1),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaisesRegex(PermissionError, "local user"):
                call()

    def test_opportunity_create_update_and_timeline(self):
        opportunity = self.service.create_opportunity(
            1,
            {
                "company": "Acme",
                "job_title": "Engineer",
                "status": APPLICATION_STATUSES[0],
                "jd_text": "A" * 100,
                "contact_info": "secret@example.com",
            },
        )
        updated = self.service.update_opportunity(
            1, opportunity["id"], {"status": APPLICATION_STATUSES[1], "notes": "call"}
        )
        events = self.service.timeline(1, opportunity["id"])

        self.assertEqual(updated["status"], APPLICATION_STATUSES[1])
        self.assertEqual([event["event_type"] for event in events], ["opportunity.created", "opportunity.updated"])
        serialized = json.dumps(events)
        self.assertNotIn("secret@example.com", serialized)
        self.assertNotIn("A" * 100, serialized)

    def test_invalid_status_is_rejected_without_partial_write(self):
        with self.assertRaisesRegex(ValueError, "status"):
            self.service.create_opportunity(
                1, {"company": "Acme", "job_title": "Engineer", "status": "invented"}
            )

        self.assertEqual(self.service.list_opportunities(1), [])
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0], 0)

    def test_opportunity_rejects_resume_owned_by_another_user(self):
        with connect(self.db_path) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Private', 'secret')"
            ).lastrowid

        with self.assertRaisesRegex(LookupError, "resume"):
            self.service.create_opportunity(
                1, {"company": "Acme", "job_title": "Engineer", "resume_id": resume_id}
            )

        self.assertEqual(self.service.list_opportunities(1), [])

    def test_event_failure_rolls_back_business_write(self):
        with patch.object(self.service, "_write_event", side_effect=RuntimeError("event failed")):
            with self.assertRaisesRegex(RuntimeError, "event failed"):
                self.service.create_opportunity(
                    1, {"company": "Acme", "job_title": "Engineer"}
                )

        self.assertEqual(self.service.list_opportunities(1), [])

    def test_unknown_legacy_status_remains_visible_for_review(self):
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title, status) VALUES (?, ?, ?, ?)",
                (1, "Legacy Co", "Engineer", "legacy-custom"),
            )

        opportunities = self.service.list_opportunities(1)

        self.assertEqual(opportunities[0]["status"], "legacy-custom")
        self.assertTrue(opportunities[0]["needs_status_review"])

    def test_resume_version_requires_owned_source_and_preserves_original(self):
        with connect(self.db_path) as conn:
            source_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Base', 'original')"
            ).lastrowid
            other_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'Other', 'private')"
            ).lastrowid

        version = self.service.create_resume_version(
            1,
            source_id,
            "tailored content",
            {"version_label": "Acme v1", "target_job_title": "Engineer", "status": "active"},
        )

        self.assertEqual(version["parent_resume_id"], source_id)
        self.assertEqual(version["content"], "tailored content")
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT content FROM resumes WHERE id = ?", (source_id,)).fetchone()[0], "original")
        with self.assertRaisesRegex(LookupError, "resume"):
            self.service.create_resume_version(1, other_id, "stolen", {})

    def test_action_completion_is_idempotent_and_records_evidence(self):
        opportunity = self.service.create_opportunity(1, {"company": "Acme", "job_title": "Engineer"})
        action = self.service.create_action_item(
            1,
            {"opportunity_id": opportunity["id"], "title": "Send follow-up", "type": "follow_up"},
        )

        first = self.service.complete_action_item(1, action["id"], "email sent")
        second = self.service.complete_action_item(1, action["id"], "different evidence")

        self.assertEqual(first, second)
        self.assertEqual(second["completion_evidence"], "email sent")
        event_types = [event["event_type"] for event in self.service.timeline(1, opportunity["id"])]
        self.assertEqual(event_types.count("action_item.completed"), 1)

    def test_validation_rejects_missing_and_oversized_inputs(self):
        with self.assertRaisesRegex(ValueError, "company"):
            self.service.create_opportunity(1, {"job_title": "Engineer"})
        with self.assertRaisesRegex(ValueError, "title"):
            self.service.create_action_item(1, {"title": "x" * 501})


class CareerApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "api.db")
        os.environ["JOBHUNTER_DB_PATH"] = self.db_path
        import importlib
        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.app_module.app.config["TESTING"] = True
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        os.environ.pop("JOBHUNTER_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_profile_opportunity_and_action_api_basics(self):
        profile = self.client.put("/api/profile", json={"target_role": "Engineer"})
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(self.client.get("/api/profile").get_json()["data"]["target_role"], "Engineer")

        created = self.client.post(
            "/api/opportunities", json={"company": "Acme", "job_title": "Engineer"}
        )
        self.assertEqual(created.status_code, 201)
        opportunity_id = created.get_json()["data"]["id"]
        listing = self.client.get("/api/opportunities").get_json()
        self.assertEqual(listing["data"][0]["id"], opportunity_id)
        self.assertEqual(tuple(listing["canonical_statuses"]), APPLICATION_STATUSES)

        action = self.client.post(
            "/api/action-items", json={"opportunity_id": opportunity_id, "title": "Follow up"}
        )
        action_id = action.get_json()["data"]["id"]
        completed = self.client.post(
            f"/api/action-items/{action_id}/complete", json={"evidence": "sent"}
        )
        self.assertEqual(completed.get_json()["data"]["status"], "completed")
        self.assertGreaterEqual(len(self.client.get(f"/api/opportunities/{opportunity_id}/timeline").get_json()["data"]), 3)

    def test_legacy_application_adapter_preserves_shape(self):
        created = self.client.post("/api/applications", json={"company": "Acme", "job_title": "Engineer"})
        self.assertTrue(created.get_json()["success"])
        application_id = created.get_json()["application_id"]

        listing = self.client.get("/api/applications/1").get_json()

        self.assertEqual(listing["data"][0]["id"], application_id)
        self.assertIn("canonical_statuses", listing)


if __name__ == "__main__":
    unittest.main()

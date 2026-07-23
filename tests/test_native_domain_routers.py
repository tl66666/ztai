from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application


class NativeDomainRouterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.settings = Settings(
            environment="test",
            db_path=root / "jobhunter.db",
            upload_folder=root / "uploads",
            export_folder=root / "exports",
        )
        self.client_context = TestClient(create_application(self.settings))
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_opportunity_routes_are_native_and_preserve_workspace_contract(self):
        created = self.client.post(
            "/api/opportunities",
            json={"company": "Acme", "job_title": "Platform Engineer"},
        )
        opportunity_id = created.json()["data"]["id"]

        listed = self.client.get("/api/opportunities")
        workspace = self.client.get(
            f"/api/opportunities/{opportunity_id}/workspace"
        )
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"][0]["id"], opportunity_id)
        self.assertEqual(workspace.status_code, 200)
        self.assertEqual(workspace.json()["opportunity"]["id"], opportunity_id)
        self.assertIn("/api/opportunities", openapi["paths"])
        self.assertIn(
            "/api/opportunities/{opportunity_id}/workspace",
            openapi["paths"],
        )

    def test_interview_routes_are_native_and_keep_retry_contract(self):
        started = self.client.post(
            "/api/interview/sessions",
            json={"job_title": "Platform Engineer"},
        )
        session_id = started.json()["session_id"]
        answer = {
            "answer": "I designed tests for a Python ASGI service.",
            "submission_id": "native-1",
            "expected_stage_index": 0,
        }

        first = self.client.post(
            f"/api/interview/sessions/{session_id}/answer", json=answer
        )
        duplicate = self.client.post(
            f"/api/interview/sessions/{session_id}/answer", json=answer
        )
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(started.status_code, 200)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.json()["idempotent"])
        self.assertIn("/api/interview/sessions", openapi["paths"])
        self.assertIn(
            "/api/interview/sessions/{session_id}/answer",
            openapi["paths"],
        )

    def test_native_json_validation_matches_legacy_contract(self):
        opportunity = self.client.post("/api/opportunities", json=[])
        interview = self.client.post("/api/interview/sessions", json=[])

        self.assertEqual(opportunity.status_code, 400)
        self.assertEqual(
            opportunity.json(),
            {"success": False, "message": "JSON body must be an object"},
        )
        self.assertEqual(interview.status_code, 400)
        self.assertEqual(
            interview.json(),
            {"success": False, "message": "JSON body must be an object"},
        )


if __name__ == "__main__":
    unittest.main()

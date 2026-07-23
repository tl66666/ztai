from __future__ import annotations

import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from backend.adapters.storage import LocalBlobStorage
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

    def test_resume_crud_routes_are_native_and_expose_typed_contracts(self):
        created = self.client.post(
            "/api/resumes",
            json={"user_id": 1, "title": "Platform", "content": "Python ASGI"},
        )
        resume_id = created.json()["resume_id"]

        listed = self.client.get("/api/resumes/1")
        detail = self.client.get(f"/api/resumes/detail/{resume_id}")
        updated = self.client.put(
            f"/api/resumes/{resume_id}",
            json={"title": "Platform v2", "content": "FastAPI and Python"},
        )
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn("file_path", listed.json()["data"][0])
        self.assertFalse(listed.json()["data"][0]["has_original"])
        self.assertEqual(detail.json()["data"]["id"], resume_id)
        self.assertEqual(updated.status_code, 200)
        update_operation = openapi["paths"]["/api/resumes/{resume_id}"]["put"]
        self.assertIn("requestBody", update_operation)

        deleted = self.client.delete(f"/api/resumes/{resume_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/resumes/detail/{resume_id}").status_code,
            404,
        )

    def test_resume_upload_uses_generated_object_key_and_preserves_original(self):
        uploaded = self.client.post(
            "/api/resumes/upload",
            data={"user_id": "1", "title": "Uploaded"},
            files={"file": ("../../unsafe name.txt", b"resume body", "text/plain")},
        )
        resume_id = uploaded.json()["resume_id"]

        with sqlite3.connect(self.settings.db_path) as connection:
            file_path = Path(
                connection.execute(
                    "SELECT file_path FROM resumes WHERE id = ?",
                    (resume_id,),
                ).fetchone()[0]
            )

        self.assertEqual(uploaded.status_code, 201)
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.parent.name, "1")
        self.assertNotIn("unsafe", file_path.name)
        original = self.client.get(f"/api/resumes/{resume_id}/original")
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original.content, b"resume body")

    def test_local_blob_storage_removes_partial_oversize_object(self):
        storage_root = Path(self.temporary_directory.name) / "bounded"
        storage = LocalBlobStorage(storage_root, max_bytes=4)

        with self.assertRaisesRegex(ValueError, "20 MB"):
            storage.store(
                BytesIO(b"12345"),
                original_name="resume.txt",
                namespace="resumes/1",
            )

        self.assertEqual(list(storage_root.rglob("*.*")), [])


if __name__ == "__main__":
    unittest.main()

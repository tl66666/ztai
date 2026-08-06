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
        self.temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
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
        import gc, shutil
        gc.collect()
        try:
            self.temporary_directory.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temporary_directory.name, ignore_errors=True)
    def test_opportunity_routes_are_native_and_preserve_workspace_contract(self):
        created = self.client.post(
            "/api/opportunities",
            json={"company": "Acme", "job_title": "Platform Engineer"},
        )
        opportunity_id = created.json()["data"]["id"]

        listed = self.client.get("/api/opportunities")
        workspace = self.client.get(f"/api/opportunities/{opportunity_id}/workspace")
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

        first = self.client.post(f"/api/interview/sessions/{session_id}/answer", json=answer)
        duplicate = self.client.post(f"/api/interview/sessions/{session_id}/answer", json=answer)
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

        exported_pdf = self.client.get(f"/api/resumes/{resume_id}/export/pdf")
        exported_docx = self.client.get(f"/api/resumes/{resume_id}/export/word")
        invalid_export = self.client.get(f"/api/resumes/{resume_id}/export/html")
        self.assertEqual(exported_pdf.status_code, 200)
        self.assertEqual(exported_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(exported_pdf.content.startswith(b"%PDF"))
        self.assertEqual(exported_docx.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats",
            exported_docx.headers["content-type"],
        )
        self.assertEqual(invalid_export.status_code, 400)

        deleted = self.client.delete(f"/api/resumes/{resume_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/resumes/detail/{resume_id}").status_code,
            404,
        )

    def test_resume_intelligence_routes_are_native_and_preserve_evidence(self):
        created = self.client.post(
            "/api/resumes",
            json={
                "title": "Platform",
                "content": "Python FastAPI 项目，负责接口测试并输出报告。",
            },
        )
        resume_id = created.json()["resume_id"]
        audited = self.client.post(
            f"/api/resumes/{resume_id}/audit",
            json={"job_title": "Backend Engineer", "jd": "Python FastAPI"},
        )
        matched = self.client.post(
            "/api/job-match",
            json={
                "resume_id": resume_id,
                "job_title": "Backend Engineer",
                "jd": "Python FastAPI",
            },
        )
        analyzed_jd = self.client.post(
            "/api/ai/analyze-jd",
            json={"jd_content": "Python FastAPI 接口测试"},
        )
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(audited.status_code, 200)
        self.assertIn("section_scores", audited.json())
        self.assertEqual(matched.status_code, 200)
        self.assertIn("match_score", matched.json())
        self.assertEqual(analyzed_jd.status_code, 200)
        self.assertIn("keywords", analyzed_jd.json())
        for path in (
            "/api/resumes/{resume_id}/audit",
            "/api/resumes/{resume_id}/improve",
            "/api/job-match",
            "/api/skills/radar",
            "/api/ai/analyze-jd",
            "/api/resume-templates",
        ):
            self.assertIn(path, openapi["paths"])

    def test_job_match_does_not_reveal_a_foreign_resume(self):
        with sqlite3.connect(self.settings.db_path) as connection:
            foreign_resume_id = connection.execute(
                """
                INSERT INTO resumes (user_id, title, content)
                VALUES (2, 'Private', 'secret')
                """
            ).lastrowid

        response = self.client.post(
            "/api/job-match",
            json={"resume_id": foreign_resume_id, "jd": "Python FastAPI"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "resume not found")

    def test_career_compatibility_routes_are_native_and_owner_scoped(self):
        profile = self.client.put(
            "/api/profile",
            json={"target_role": "Platform Engineer"},
        )
        application = self.client.post(
            "/api/applications",
            json={"company": "Acme", "job_title": "Platform Engineer"},
        )
        application_id = application.json()["application_id"]
        listed = self.client.get("/api/applications/1")
        advanced = self.client.post(f"/api/applications/{application_id}/advance")
        action = self.client.post(
            "/api/action-items",
            json={
                "application_id": application_id,
                "title": "Follow up",
            },
        )
        salary = self.client.post(
            "/api/salary/evaluate",
            json={"city": "上海", "experience": "1-3年", "skills_count": 4},
        )
        denied = self.client.get("/api/applications/2")
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(
            self.client.get("/api/profile").json()["data"]["target_role"],
            "Platform Engineer",
        )
        self.assertEqual(application.status_code, 200)
        self.assertEqual(listed.json()["data"][0]["id"], application_id)
        self.assertEqual(advanced.status_code, 200)
        self.assertEqual(action.status_code, 201)
        self.assertGreater(salary.json()["range"]["avg"], 0)
        self.assertEqual(denied.status_code, 403)
        for path in (
            "/api/profile",
            "/api/action-items",
            "/api/applications",
            "/api/applications/{application_id}/advance",
            "/api/salary/evaluate",
        ):
            self.assertIn(path, openapi["paths"])

    def test_career_insights_routes_are_native_and_keep_read_models(self):
        application = self.client.post(
            "/api/applications",
            json={"company": "Acme", "job_title": "Platform Engineer"},
        )
        application_id = application.json()["application_id"]

        dashboard = self.client.get("/api/dashboard/1")
        report = self.client.post("/api/career/report/1")
        coach = self.client.post(f"/api/applications/{application_id}/coach")
        denied = self.client.get("/api/dashboard/2")
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("career_pulse", dashboard.json())
        self.assertEqual(report.status_code, 200)
        self.assertIn("求职作战报告", report.json()["report"])
        self.assertEqual(coach.status_code, 200)
        self.assertEqual(coach.json()["company"], "Acme")
        self.assertEqual(denied.status_code, 403)
        for path in (
            "/api/dashboard/{user_id}",
            "/api/career/report/{user_id}",
            "/api/applications/{application_id}/coach",
        ):
            self.assertIn(path, openapi["paths"])

    def test_resume_upload_uses_generated_object_key_and_preserves_original(self):
        uploaded = self.client.post(
            "/api/resumes/upload",
            data={"user_id": "1", "title": "Uploaded"},
            files={"file": ("../../unsafe name.txt", b"resume body", "text/plain")},
        )
        resume_id = uploaded.json()["resume_id"]

        with sqlite3.connect(self.settings.db_path) as connection:
            blob_token = connection.execute(
                "SELECT file_path FROM resumes WHERE id = ?",
                (resume_id,),
            ).fetchone()[0]

        self.assertEqual(uploaded.status_code, 201)
        reference = self.client.app.state.container.blob_storage.restore(
            blob_token,
            owner_id=1,
        )
        self.assertTrue(reference.object_key.startswith("owners/1/resumes/"))
        self.assertNotIn("unsafe", reference.object_key)
        self.assertNotIn(str(self.settings.upload_folder), blob_token)
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
                namespace="resumes",
                owner_id=1,
            )

        self.assertEqual(list(storage_root.rglob("*.*")), [])


if __name__ == "__main__":
    unittest.main()

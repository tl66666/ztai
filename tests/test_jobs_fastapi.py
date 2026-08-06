from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from backend.application.jobs.runner import JobRunner
from backend.core.settings import Settings
from backend.main import create_application


class BackgroundJobFastAPITests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        )
        root = Path(self.temporary_directory.name)
        self.settings = Settings(
            environment="test",
            db_path=root / "jobhunter.db",
            upload_folder=root / "uploads",
            export_folder=root / "exports",
            ai_config_path=root / "ai-config.json",
        )
        self.client_context = TestClient(create_application(self.settings))
        self.client = self.client_context.__enter__()
        self.container = self.client.app.state.container
        self.runner = JobRunner(
            self.container.job_queue,
            self.container.jobs.execute,
            worker_id="test-worker",
            lease_seconds=30,
            heartbeat_seconds=5,
            retry_delay_seconds=0,
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        import gc, shutil
        gc.collect()
        try:
            self.temporary_directory.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temporary_directory.name, ignore_errors=True)

    def test_resume_analysis_has_202_status_and_worker_completion(self):
        resume = self.client.post(
            "/api/resumes",
            json={"title": "异步分析", "content": "Python FastAPI 项目"},
        ).json()
        submitted = self.client.post(
            "/api/jobs/resume-analysis",
            headers={"Idempotency-Key": "analysis-1"},
            json={"resume_id": resume["resume_id"], "job_title": "后端工程师"},
        )

        self.assertEqual(submitted.status_code, 202)
        task_id = submitted.json()["task_id"]
        self.assertEqual(
            self.client.get(f"/api/jobs/{task_id}").json()["task"]["status"],
            "queued",
        )
        self.assertTrue(self.runner.run_once())
        completed = self.client.get(f"/api/jobs/{task_id}")
        self.assertEqual(completed.json()["task"]["status"], "succeeded")
        self.assertIn("analysis", completed.json()["task"]["result"])

    def test_document_conversion_runs_durably_and_old_sync_route_remains(self):
        document = Document()
        document.add_paragraph("跨平台文档转换")
        source = BytesIO()
        document.save(source)
        source_bytes = source.getvalue()
        submitted = self.client.post(
            "/api/jobs/document-conversion",
            data={"target_format": "pdf"},
            files={
                "file": (
                    "resume.docx",
                    source_bytes,
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document",
                )
            },
        )

        self.assertEqual(submitted.status_code, 202)
        task_id = submitted.json()["task_id"]
        self.assertTrue(self.runner.run_once())
        completed = self.client.get(f"/api/jobs/{task_id}").json()["task"]
        downloaded = self.client.get(f"/api/jobs/{task_id}/result")
        synchronous = self.client.post(
            "/api/convert/word-to-pdf",
            files={"file": ("resume.docx", source_bytes)},
        )

        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(completed["result"]["media_type"], "application/pdf")
        self.assertNotIn("blob_ref", completed["result"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertTrue(downloaded.content.startswith(b"%PDF"))
        self.assertEqual(synchronous.status_code, 200)
        self.assertTrue(synchronous.content.startswith(b"%PDF"))

    def test_job_can_be_cancelled_before_worker_leases_it(self):
        resume = self.client.post(
            "/api/resumes",
            json={"title": "取消", "content": "内容"},
        ).json()
        submitted = self.client.post(
            "/api/jobs/resume-analysis",
            json={"resume_id": resume["resume_id"]},
        ).json()

        cancelled = self.client.delete(f"/api/jobs/{submitted['task_id']}")

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["task"]["status"], "cancelled")
        self.assertFalse(self.runner.run_once())


if __name__ == "__main__":
    unittest.main()

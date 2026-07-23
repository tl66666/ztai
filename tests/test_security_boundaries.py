from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

import app as app_module
from backend.core.settings import Settings
from backend.main import create_application

ROOT = Path(__file__).resolve().parents[1]


class LocalSecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.original_db_path = app_module.DB_PATH
        self.original_upload_folder = app_module.UPLOAD_FOLDER
        app_module.DB_PATH = os.path.join(self.temp_dir.name, "jobhunter.db")
        app_module.UPLOAD_FOLDER = os.path.join(self.temp_dir.name, "uploads")
        os.makedirs(app_module.UPLOAD_FOLDER, exist_ok=True)
        app_module.app.config["TESTING"] = True
        app_module.app.config["UPLOAD_FOLDER"] = app_module.UPLOAD_FOLDER
        app_module.init_db()
        self.client = app_module.app.test_client()
        root = Path(self.temp_dir.name)
        self.asgi_client = TestClient(
            create_application(
                Settings(
                    environment="test",
                    db_path=Path(app_module.DB_PATH),
                    upload_folder=Path(app_module.UPLOAD_FOLDER),
                    export_folder=root / "exports",
                )
            )
        )
        self.asgi_client.__enter__()

    def tearDown(self):
        self.asgi_client.__exit__(None, None, None)
        app_module.DB_PATH = self.original_db_path
        app_module.UPLOAD_FOLDER = self.original_upload_folder
        app_module.app.config["UPLOAD_FOLDER"] = self.original_upload_folder
        self.temp_dir.cleanup()

    def test_audio_download_cannot_escape_upload_directory(self):
        secret_path = Path(self.temp_dir.name) / "secret.txt"
        secret_path.write_text("outside-upload-secret", encoding="utf-8")

        response = self.client.get(
            "/api/uploads/%2e%2e%2fsecret.txt/download/original",
            buffered=True,
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"outside-upload-secret", response.data)
        response.close()

    def test_legacy_write_apis_reject_client_selected_user(self):
        resume_response = self.client.post(
            "/api/resumes",
            json={"user_id": 2, "title": "foreign", "content": "content"},
        )
        training_responses = (
            self.asgi_client.post(
                "/api/interview/practice-feedback",
                json={"user_id": 2, "question": "q", "answer": "long enough answer"},
            ),
            self.asgi_client.post(
                "/api/interview/analyze-audio",
                files={"audio": ("answer.wav", BytesIO(b"RIFF"), "audio/wav")},
                data={
                    "user_id": "2",
                    "transcript": "audio transcript",
                },
            ),
        )

        self.assertEqual(resume_response.status_code, 403)
        resume_response.close()
        for response in training_responses:
            with self.subTest(path=response.request.url.path):
                self.assertEqual(response.status_code, 403)
            response.close()

        with sqlite3.connect(app_module.DB_PATH) as conn:
            for table in ("resumes", "practice_records", "audio_records"):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_legacy_reads_and_deletes_cannot_access_foreign_records(self):
        with sqlite3.connect(app_module.DB_PATH) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes(user_id, title, content) VALUES (2, 'foreign', 'secret')"
            ).lastrowid
            practice_id = conn.execute(
                "INSERT INTO practice_records(user_id, category, question, answer, score) "
                "VALUES (2, 'general', 'q', 'a', 50)"
            ).lastrowid
            conn.commit()

        legacy_requests = (
            self.client.get("/api/resumes/2"),
            self.client.get(f"/api/resumes/detail/{resume_id}"),
            self.client.delete(f"/api/resumes/{resume_id}"),
            self.client.post("/api/career/report/2"),
            self.client.get("/api/applications/2"),
        )
        training_requests = (
            self.asgi_client.get("/api/training-records/2"),
            self.asgi_client.delete(
                f"/api/training-records/practice/{practice_id}"
            ),
            self.asgi_client.delete("/api/training-records/2/clear"),
        )

        for response in legacy_requests:
            with self.subTest(path=response.request.path):
                self.assertIn(response.status_code, {403, 404})
            response.close()
        for response in training_requests:
            with self.subTest(path=response.request.url.path):
                self.assertIn(response.status_code, {403, 404})
            response.close()

        with sqlite3.connect(app_module.DB_PATH) as conn:
            resume_count = conn.execute(
                "SELECT COUNT(*) FROM resumes WHERE id = ?", (resume_id,)
            ).fetchone()[0]
            practice_count = conn.execute(
                "SELECT COUNT(*) FROM practice_records WHERE id = ?",
                (practice_id,),
            ).fetchone()[0]
            self.assertEqual(resume_count, 1)
            self.assertEqual(practice_count, 1)


class PortableRuntimeContractTests(unittest.TestCase):
    def test_manual_server_rejects_non_loopback_and_never_enables_debugger(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("def validate_server_host", source)
        self.assertRegex(source, r"app\.run\(debug=False, host=host, port=LOCAL_PORT\)")

        validator = getattr(app_module, "validate_server_host", None)
        self.assertIsNotNone(validator)
        self.assertEqual(validator("127.0.0.1"), "127.0.0.1")
        with self.assertRaises(ValueError):
            validator("0.0.0.0")

    def test_frontend_dependencies_are_local_and_have_runtime_fallbacks(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
        resume_controller = (
            ROOT / "static" / "js" / "resume_controller.js"
        ).read_text(encoding="utf-8")

        self.assertNotIn("unpkg.com", html)
        self.assertNotIn("cdn.jsdelivr.net", html)
        for asset in ("vendor/lucide.min.js", "vendor/chart.umd.min.js"):
            self.assertIn(asset, html)
            path = ROOT / "static" / "js" / asset
            self.assertTrue(path.is_file(), asset)
            self.assertGreater(path.stat().st_size, 1000, asset)
        self.assertIn("function renderIcons", script)
        self.assertIn("window.Chart", resume_controller)


if __name__ == "__main__":
    unittest.main()

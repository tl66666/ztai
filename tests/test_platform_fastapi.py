from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application


class PlatformFastAPITests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
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

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_catalog_config_and_report_routes_are_native(self):
        profiles = self.client.get("/api/career/profiles")
        questions = self.client.get("/api/questions", params={"category": "test"})
        report = self.client.post(
            "/api/ai/generate-test-report",
            json={"project_info": "跨平台项目"},
        )
        providers = self.client.get("/api/config/providers")
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(profiles.status_code, 200)
        self.assertEqual(profiles.json()["default"], "tech")
        self.assertGreaterEqual(len(profiles.json()["profiles"]), 6)
        self.assertEqual(questions.status_code, 200)
        self.assertEqual(questions.json()["data"][0]["question"], "如何设计 Web 系统的测试用例？")
        self.assertIn("跨平台项目", report.json()["content"])
        self.assertTrue(providers.json()["success"])
        self.assertIn("/api/config/providers", openapi["paths"])
        self.assertIn("/api/uploads/{filename}", openapi["paths"])

    def test_ai_configuration_is_runtime_scoped_and_clearable(self):
        configured = self.client.post(
            "/api/config/ai-key",
            json={
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "local-test-key",
            },
        )
        status = self.client.get("/api/config/ai-status")
        cleared = self.client.post(
            "/api/config/ai-key",
            json={"provider": "glm", "api_key": ""},
        )

        self.assertEqual(configured.status_code, 200)
        self.assertTrue(configured.json()["ai_enabled"])
        self.assertEqual(status.json()["provider"], "deepseek")
        self.assertFalse(cleared.json()["ai_enabled"])
        self.assertFalse(self.settings.ai_config_path.exists())

    def test_upload_reads_are_scoped_to_the_configured_storage_root(self):
        audio = self.settings.upload_folder / "answer.wav"
        audio.write_bytes(b"RIFF-test")

        response = self.client.get("/api/uploads/answer.wav")
        download = self.client.get(
            "/api/uploads/answer.wav/download/original"
        )
        traversal = self.client.get(
            "/api/uploads/%2E%2E%2Fjobhunter.db"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"RIFF-test")
        self.assertEqual(download.status_code, 200)
        self.assertIn(
            "attachment",
            download.headers["content-disposition"],
        )
        self.assertEqual(traversal.status_code, 404)

    def test_wsgi_and_static_fallback_are_not_mounted(self):
        self.assertEqual(self.client.get("/").status_code, 404)
        self.assertEqual(self.client.get("/unknown-static-file").status_code, 404)


if __name__ == "__main__":
    unittest.main()

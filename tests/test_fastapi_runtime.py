from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application


class FastAPIRuntimeTests(unittest.TestCase):
    def test_native_health_and_legacy_routes_share_one_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(
                environment="test",
                db_path=root / "jobhunter.db",
                upload_folder=root / "uploads",
                export_folder=root / "exports",
            )

            with TestClient(create_application(settings)) as client:
                health = client.get("/api/v1/healthz")
                providers = client.get("/api/config/providers")

            self.assertEqual(health.status_code, 200)
            self.assertEqual(
                health.json(),
                {"status": "ok", "service": "jobhunter-api"},
            )
            self.assertEqual(providers.status_code, 200)
            self.assertTrue(providers.json()["success"])

    def test_readiness_reports_the_initialized_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(
                environment="test",
                db_path=root / "jobhunter.db",
                upload_folder=root / "uploads",
                export_folder=root / "exports",
            )

            with TestClient(create_application(settings)) as client:
                response = client.get("/api/v1/readyz")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json(),
                {
                    "status": "ready",
                    "checks": {"database": "ok"},
                },
            )

    def test_cloudflare_origin_is_allowed_by_runtime_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(
                environment="test",
                db_path=root / "jobhunter.db",
                upload_folder=root / "uploads",
                export_folder=root / "exports",
                allowed_origins=("https://career.example.com",),
                allowed_hosts=("testserver",),
            )

            with TestClient(create_application(settings)) as client:
                response = client.options(
                    "/api/config/providers",
                    headers={
                        "Origin": "https://career.example.com",
                        "Access-Control-Request-Method": "GET",
                    },
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers["access-control-allow-origin"],
                "https://career.example.com",
            )

    def test_environment_settings_resolve_paths_and_parse_network_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = {
                "JOBHUNTER_ENV": "production",
                "JOBHUNTER_PROJECT_ROOT": str(root),
                "JOBHUNTER_DB_PATH": "data/jobhunter.db",
                "JOBHUNTER_UPLOAD_FOLDER": "data/uploads",
                "JOBHUNTER_EXPORT_FOLDER": "data/exports",
                "JOBHUNTER_ALLOWED_ORIGINS": (
                    "https://career.example.com, https://preview.example.com "
                ),
                "JOBHUNTER_ALLOWED_HOSTS": "api.example.com,localhost",
                "JOBHUNTER_API_DOCS": "false",
            }

            with patch.dict(os.environ, environment, clear=True):
                settings = Settings.from_environment()

            resolved_root = root.resolve()
            self.assertEqual(
                settings.db_path,
                resolved_root / "data" / "jobhunter.db",
            )
            self.assertEqual(
                settings.upload_folder,
                resolved_root / "data" / "uploads",
            )
            self.assertEqual(
                settings.export_folder,
                resolved_root / "data" / "exports",
            )
            self.assertEqual(
                settings.allowed_origins,
                ("https://career.example.com", "https://preview.example.com"),
            )
            self.assertEqual(settings.allowed_hosts, ("api.example.com", "localhost"))
            self.assertFalse(settings.api_docs_enabled)

    def test_compatibility_runtime_rejects_public_bind_addresses(self):
        with patch.dict(
            os.environ,
            {"JOBHUNTER_HOST": "0.0.0.0"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "loopback"):
                Settings.from_environment()

    def test_application_factories_keep_legacy_runtime_state_isolated(self):
        with (
            tempfile.TemporaryDirectory() as first_directory,
            tempfile.TemporaryDirectory() as second_directory,
        ):
            first_root = Path(first_directory)
            second_root = Path(second_directory)
            first_settings = Settings(
                environment="test",
                db_path=first_root / "jobhunter.db",
                upload_folder=first_root / "uploads",
                export_folder=first_root / "exports",
            )
            second_settings = Settings(
                environment="test",
                db_path=second_root / "jobhunter.db",
                upload_folder=second_root / "uploads",
                export_folder=second_root / "exports",
            )

            first_application = create_application(first_settings)
            create_application(second_settings)
            with TestClient(first_application) as client:
                response = client.get("/api/config/providers")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(first_settings.db_path.exists())
            self.assertFalse(second_settings.db_path.exists())

    def test_application_factories_keep_ai_configuration_isolated(self):
        with (
            tempfile.TemporaryDirectory() as first_directory,
            tempfile.TemporaryDirectory() as second_directory,
        ):
            first_root = Path(first_directory)
            second_root = Path(second_directory)
            first_settings = Settings(
                environment="test",
                db_path=first_root / "jobhunter.db",
                upload_folder=first_root / "uploads",
                export_folder=first_root / "exports",
                ai_config_path=first_root / "runtime" / "ai.json",
            )
            second_settings = Settings(
                environment="test",
                db_path=second_root / "jobhunter.db",
                upload_folder=second_root / "uploads",
                export_folder=second_root / "exports",
                ai_config_path=second_root / "runtime" / "ai.json",
            )
            first_application = create_application(first_settings)
            second_application = create_application(second_settings)

            with (
                TestClient(first_application) as first_client,
                TestClient(second_application) as second_client,
            ):
                configured = first_client.post(
                    "/api/config/ai-key",
                    json={
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "api_key": "first-runtime-key",
                    },
                )
                first_status = first_client.get("/api/config/ai-status")
                second_status = second_client.get("/api/config/ai-status")

            self.assertEqual(configured.status_code, 200)
            self.assertTrue(first_status.json()["ai_enabled"])
            self.assertEqual(first_status.json()["provider"], "deepseek")
            self.assertFalse(second_status.json()["ai_enabled"])
            self.assertEqual(second_status.json()["provider"], "glm")
            self.assertTrue(first_settings.ai_config_path.is_file())
            self.assertFalse(second_settings.ai_config_path.exists())


if __name__ == "__main__":
    unittest.main()

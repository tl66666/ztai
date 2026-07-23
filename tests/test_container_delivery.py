from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContainerDeliveryTests(unittest.TestCase):
    def test_container_runs_as_non_root_with_one_cross_platform_entry(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn('CMD ["uv", "run", "--no-sync", "python", "-m", "backend.cli"]', dockerfile)
        self.assertNotIn("powershell", dockerfile.lower())
        self.assertNotIn("sudo", dockerfile.lower())

    def test_compose_keeps_backend_on_loopback_and_hardens_runtime(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn('"127.0.0.1:8000:8000"', compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("- ALL", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("jobhunter-data:/app/data", compose)

    def test_production_environment_requires_cloudflare_access(self):
        environment = (ROOT / "deploy" / "backend.env.example").read_text(encoding="utf-8")

        self.assertIn("JOBHUNTER_AUTH_MODE=cloudflare_access", environment)
        self.assertIn("JOBHUNTER_ALLOWED_ORIGINS=https://", environment)
        self.assertIn("JOBHUNTER_ALLOWED_HOSTS=", environment)
        self.assertNotIn("JOBHUNTER_ALLOWED_ORIGINS=*", environment)


if __name__ == "__main__":
    unittest.main()

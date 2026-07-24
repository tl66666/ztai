from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application
from backend.security import (
    AuthenticationError,
    CloudflareAccessPrincipalProvider,
)


class _RejectingProvider:
    def authenticate(self, headers):
        del headers
        raise AuthenticationError("authentication_required")


class PrincipalSecurityTests(unittest.TestCase):
    def test_api_is_protected_while_health_endpoint_stays_public(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(
                environment="test",
                db_path=root / "jobhunter.db",
                upload_folder=root / "uploads",
                export_folder=root / "exports",
            )
            application = create_application(
                settings,
                principal_provider=_RejectingProvider(),
            )

            with TestClient(application) as client:
                health = client.get("/api/v1/healthz")
                protected = client.get("/api/config/ai-status")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(protected.status_code, 401)
        self.assertEqual(
            protected.json()["code"],
            "authentication_failed",
        )

    def test_cloudflare_access_provider_validates_identity_allowlist(self):
        provider = CloudflareAccessPrincipalProvider(
            team_domain="team.cloudflareaccess.com",
            audience="audience-id",
            allowed_emails=("owner@example.com",),
        )
        provider._jwk_client = SimpleNamespace(
            get_signing_key_from_jwt=lambda assertion: SimpleNamespace(
                key="public-key"
            )
        )
        claims = {
            "sub": "cloudflare-user",
            "email": "Owner@Example.com",
        }

        with patch("backend.security.principal.jwt.decode", return_value=claims):
            principal = provider.authenticate(
                {"cf-access-jwt-assertion": "signed-token"}
            )

        self.assertEqual(principal.subject, "cloudflare-user")
        self.assertEqual(principal.email, "owner@example.com")
        self.assertEqual(principal.user_id, 1)

    def test_cloudflare_access_provider_rejects_unlisted_identity(self):
        provider = CloudflareAccessPrincipalProvider(
            team_domain="team.cloudflareaccess.com",
            audience="audience-id",
            allowed_emails=("owner@example.com",),
        )
        provider._jwk_client = SimpleNamespace(
            get_signing_key_from_jwt=lambda assertion: SimpleNamespace(
                key="public-key"
            )
        )
        claims = {
            "sub": "cloudflare-user",
            "email": "other@example.com",
        }

        with (
            patch(
                "backend.security.principal.jwt.decode",
                return_value=claims,
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "identity_not_allowed",
            ),
        ):
            provider.authenticate(
                {"authorization": "Bearer signed-token"}
            )

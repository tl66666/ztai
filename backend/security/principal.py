from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import jwt


class AuthenticationError(ValueError):
    """Raised when a request cannot establish an allowed identity."""


@dataclass(frozen=True)
class Principal:
    subject: str
    email: str
    user_id: int


class PrincipalProvider(Protocol):
    def authenticate(self, headers: Mapping[str, str]) -> Principal: ...


class LocalPrincipalProvider:
    """Development adapter preserving the existing single-user behavior."""

    def __init__(self, user_id: int = 1):
        self._user_id = int(user_id)

    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        del headers
        return Principal(
            subject="local-user",
            email="local@localhost",
            user_id=self._user_id,
        )


class CloudflareAccessPrincipalProvider:
    """Validate Cloudflare Access JWTs at the Ubuntu API boundary."""

    def __init__(
        self,
        *,
        team_domain: str,
        audience: str,
        allowed_emails: tuple[str, ...],
        user_id: int = 1,
    ):
        normalized_domain = team_domain.removeprefix("https://").rstrip("/")
        self._issuer = f"https://{normalized_domain}"
        self._audience = audience
        self._allowed_emails = {
            email.strip().lower() for email in allowed_emails if email.strip()
        }
        self._user_id = int(user_id)
        self._jwk_client = jwt.PyJWKClient(
            f"{self._issuer}/cdn-cgi/access/certs",
            cache_jwk_set=True,
            lifespan=300,
        )

    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        assertion = headers.get("cf-access-jwt-assertion", "").strip()
        if not assertion:
            authorization = headers.get("authorization", "")
            scheme, _, credentials = authorization.partition(" ")
            if scheme.lower() == "bearer":
                assertion = credentials.strip()
        if not assertion:
            raise AuthenticationError("authentication_required")
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(assertion)
            claims = jwt.decode(
                assertion,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("invalid_access_assertion") from exc

        subject = str(claims.get("sub") or "").strip()
        email = str(claims.get("email") or "").strip().lower()
        if not subject or not email:
            raise AuthenticationError("identity_claims_missing")
        if email not in self._allowed_emails:
            raise AuthenticationError("identity_not_allowed")
        return Principal(
            subject=subject,
            email=email,
            user_id=self._user_id,
        )

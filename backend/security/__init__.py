"""Request identity and authentication adapters."""

from .principal import (
    AuthenticationError,
    CloudflareAccessPrincipalProvider,
    LocalPrincipalProvider,
    Principal,
    PrincipalProvider,
)

__all__ = [
    "AuthenticationError",
    "CloudflareAccessPrincipalProvider",
    "LocalPrincipalProvider",
    "Principal",
    "PrincipalProvider",
]

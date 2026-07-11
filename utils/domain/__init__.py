"""Shared career-domain data primitives."""

from .database import (
    APPLICATION_STATUSES,
    LEGACY_STATUS_MAP,
    connect,
    ensure_column,
    migrate_database,
)

__all__ = [
    "APPLICATION_STATUSES",
    "LEGACY_STATUS_MAP",
    "connect",
    "ensure_column",
    "migrate_database",
]

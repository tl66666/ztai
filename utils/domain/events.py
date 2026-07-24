from __future__ import annotations

from typing import Any


def apply_event_to_actions(
    repository_or_connection: Any,
    user_id: int,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int | str,
    payload: dict[str, Any] | None,
) -> int:
    """Complete only action items whose linkage makes the event unambiguous."""
    method = getattr(repository_or_connection, "apply_to_actions", None)
    if callable(method):
        return int(
            method(
                user_id,
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
            )
        )

    from backend.adapters.persistence.legacy_event_repository import (
        LegacySqliteEventRepository,
    )

    return LegacySqliteEventRepository(repository_or_connection).apply_to_actions(
        user_id,
        event_type,
        aggregate_type,
        aggregate_id,
        payload,
    )


__all__ = ["apply_event_to_actions"]

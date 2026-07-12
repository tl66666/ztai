from __future__ import annotations

import json
import sqlite3
from typing import Any


_EVENT_ACTION_TYPES = {
    "resume.version_created": ("create_resume_version", "resume_version"),
    "interview.completed": ("interview", "interview_plan", "mock_interview"),
    "career_report.saved": ("career_report", "save_career_report"),
}


def apply_event_to_actions(
    conn: sqlite3.Connection,
    user_id: int,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int | str,
    payload: dict[str, Any] | None,
) -> int:
    """Complete only action items whose linkage makes the event unambiguous."""
    action_types = _EVENT_ACTION_TYPES.get(event_type)
    if not action_types:
        return 0

    application_id: int | None = None
    if event_type == "resume.version_created" and aggregate_type == "opportunity":
        application_id = _integer_id(aggregate_id)
    elif event_type == "interview.completed" and aggregate_type == "interview_session":
        row = conn.execute(
            "SELECT application_id FROM interview_sessions WHERE id = ? AND user_id = ?",
            (aggregate_id, user_id),
        ).fetchone()
        application_id = row[0] if row else None
    elif event_type == "career_report.saved" and aggregate_type == "career_report":
        action_id = _integer_id((payload or {}).get("action_id"))
        if action_id is None:
            return 0
    else:
        return 0

    if event_type != "career_report.saved" and application_id is None:
        return 0

    evidence_values: dict[str, Any] = {"event": event_type}
    for key in ("resume_id", "score", "report_type"):
        value = (payload or {}).get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            if value is not None:
                evidence_values[key] = value
    evidence = json.dumps(evidence_values, ensure_ascii=False, separators=(",", ":"))[:500]
    placeholders = ",".join("?" for _ in action_types)
    action_status_clause = (
        "status = 'pending'"
        if event_type == "career_report.saved"
        else "status IN ('pending', 'in_progress')"
    )
    clauses = ["user_id = ?", action_status_clause]
    params: list[Any] = [user_id]
    clauses.append(f"action_type IN ({placeholders})")
    params.extend(action_types)
    if event_type == "career_report.saved":
        clauses.append("id = ?")
        params.append(action_id)
    else:
        clauses.append("application_id = ?")
        params.append(application_id)
    cursor = conn.execute(
        f"""
        UPDATE action_items
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
            completion_evidence = ?, source = 'domain_event', updated_at = CURRENT_TIMESTAMP
        WHERE {' AND '.join(clauses)}
        """,
        [evidence, *params],
    )
    return cursor.rowcount


def _integer_id(value: int | str) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


__all__ = ["apply_event_to_actions"]

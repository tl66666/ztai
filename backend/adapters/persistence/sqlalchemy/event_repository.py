from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from .career_models import action_items, domain_events
from .training_models import interview_sessions

_EVENT_ACTION_TYPES = {
    "resume.version_created": (
        "create_resume_version",
        "resume_version",
    ),
    "interview.completed": (
        "interview",
        "interview_plan",
        "mock_interview",
    ),
    "career_report.saved": (
        "career_report",
        "save_career_report",
    ),
}


class SqlAlchemyEventRepository:
    """Persist domain events and project them onto linked action items."""

    def __init__(self, session: Session):
        self._session = session

    def add(
        self,
        user_id: int,
        aggregate_type: str,
        aggregate_id: int | str,
        event_type: str,
        payload: dict[str, Any] | None,
    ) -> None:
        self._execute(
            insert(domain_events).values(
                user_id=user_id,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                event_type=event_type,
                payload_json=self._dump(payload or {}),
                source=(payload or {}).get("source"),
            )
        )

    def apply_to_actions(
        self,
        user_id: int,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int | str,
        payload: dict[str, Any] | None,
    ) -> int:
        action_types = _EVENT_ACTION_TYPES.get(event_type)
        if not action_types:
            return 0
        action_id = self._integer_id((payload or {}).get("action_id"))
        if action_id is None:
            return 0

        application_id = self._application_id(
            user_id,
            event_type,
            aggregate_type,
            aggregate_id,
        )
        if application_id is False:
            return 0
        if event_type != "career_report.saved" and application_id is None:
            return 0

        evidence_values: dict[str, Any] = {"event": event_type}
        for key in ("resume_id", "score", "report_type"):
            value = (payload or {}).get(key)
            if value is not None and isinstance(value, (str, int, float, bool)):
                evidence_values[key] = value
        evidence = self._dump(evidence_values)[:500]

        conditions = [
            action_items.c.user_id == user_id,
            action_items.c.action_type.in_(action_types),
            action_items.c.id == action_id,
        ]
        if event_type == "career_report.saved":
            conditions.append(action_items.c.status == "pending")
        else:
            conditions.append(action_items.c.status.in_(("pending", "in_progress")))
            conditions.append(action_items.c.application_id == application_id)

        result = self._execute(
            update(action_items)
            .where(*conditions)
            .values(
                status="completed",
                completed_at=func.current_timestamp(),
                completion_evidence=evidence,
                source="domain_event",
                updated_at=func.current_timestamp(),
            )
        )
        return int(result.rowcount or 0)

    def record_and_apply(
        self,
        user_id: int,
        aggregate_type: str,
        aggregate_id: int | str,
        event_type: str,
        payload: dict[str, Any] | None,
    ) -> int:
        self.add(user_id, aggregate_type, aggregate_id, event_type, payload)
        return self.apply_to_actions(
            user_id,
            event_type,
            aggregate_type,
            aggregate_id,
            payload,
        )

    def _application_id(
        self,
        user_id: int,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int | str,
    ) -> int | None | bool:
        if event_type == "resume.version_created":
            return self._integer_id(aggregate_id) if aggregate_type == "opportunity" else False
        if event_type == "interview.completed":
            if aggregate_type != "interview_session":
                return False
            row = self._execute(
                select(interview_sessions.c.application_id).where(
                    interview_sessions.c.id == aggregate_id,
                    interview_sessions.c.user_id == user_id,
                )
            ).fetchone()
            return self._integer_id(row[0]) if row and row[0] is not None else None
        if event_type == "career_report.saved":
            return None if aggregate_type == "career_report" else False
        return False

    def _execute(self, statement):
        return self._session.execute(statement)

    @staticmethod
    def _integer_id(value: int | str) -> int | None:
        try:
            result = int(value)
        except (TypeError, ValueError):
            return None
        return result if result > 0 else None

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


__all__ = ["SqlAlchemyEventRepository"]

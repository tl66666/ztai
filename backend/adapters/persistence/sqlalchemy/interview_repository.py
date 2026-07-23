from __future__ import annotations

from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from .career_models import action_items
from .core_models import job_applications, resumes
from .event_repository import SqlAlchemyEventRepository
from .training_models import (
    audio_records,
    interview_sessions,
    interviews,
    practice_records,
)


class SqlAlchemyInterviewRepository:
    """All persistence required by one mock-interview transaction."""

    _TRAINING_TABLES = {
        "interview": interviews,
        "practice": practice_records,
        "audio": audio_records,
    }

    def __init__(
        self,
        session: Session,
        events: SqlAlchemyEventRepository | None = None,
    ):
        self._session = session
        self.events = events or SqlAlchemyEventRepository(session)

    def get_resume(self, resume_id: int) -> dict[str, Any] | None:
        return self._one(select(resumes).where(resumes.c.id == resume_id))

    def get_opportunity(self, opportunity_id: int) -> dict[str, Any] | None:
        return self._one(select(job_applications).where(job_applications.c.id == opportunity_id))

    def get_action(self, action_id: int) -> dict[str, Any] | None:
        return self._one(select(action_items).where(action_items.c.id == action_id))

    def create_session(self, values: dict[str, Any]) -> int:
        result = self._session.execute(insert(interview_sessions).values(**values))
        return int(result.inserted_primary_key[0])

    def get_session(
        self,
        session_id: int,
        *,
        for_update: bool = False,
    ) -> dict[str, Any] | None:
        statement = select(interview_sessions).where(interview_sessions.c.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return self._one(statement)

    def update_session(
        self,
        session_id: int,
        user_id: int,
        *,
        status: str,
        current_stage: str,
        conversation_json: str,
        score: int | None,
        feedback: str,
        completed: bool,
    ) -> None:
        values: dict[str, Any] = {
            "status": status,
            "current_stage": current_stage,
            "conversation_json": conversation_json,
            "score": score,
            "feedback": feedback,
            "updated_at": func.current_timestamp(),
        }
        if completed:
            values["completed_at"] = func.current_timestamp()
        self._session.execute(
            update(interview_sessions)
            .where(
                interview_sessions.c.id == session_id,
                interview_sessions.c.user_id == user_id,
            )
            .values(**values)
        )

    def update_state(self, session_id: int, user_id: int, conversation_json: str) -> None:
        self._session.execute(
            update(interview_sessions)
            .where(
                interview_sessions.c.id == session_id,
                interview_sessions.c.user_id == user_id,
            )
            .values(
                conversation_json=conversation_json,
                updated_at=func.current_timestamp(),
            )
        )

    def add_completed_interview(
        self,
        *,
        user_id: int,
        resume_id: int | None,
        job_title: str,
        conversation: str,
        score: int,
        feedback: str,
        source_session_id: int,
    ) -> None:
        self._session.execute(
            insert(interviews).values(
                user_id=user_id,
                resume_id=resume_id,
                job_title=job_title,
                conversation=conversation,
                score=score,
                feedback=feedback,
                source_session_id=str(source_session_id),
            )
        )

    def list_open(self, user_id: int) -> list[dict[str, Any]]:
        statement = (
            select(interview_sessions)
            .where(
                interview_sessions.c.user_id == user_id,
                interview_sessions.c.status != "completed",
            )
            .order_by(
                interview_sessions.c.updated_at.desc(),
                interview_sessions.c.id.desc(),
            )
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    def recent_training_rows(
        self,
        kind: str,
        user_id: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = self._TRAINING_TABLES[kind]
        statement = (
            select(table)
            .where(table.c.user_id == user_id)
            .order_by(table.c.created_at.desc(), table.c.id.desc())
            .limit(limit)
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    def record_event(
        self,
        user_id: int,
        aggregate_type: str,
        aggregate_id: int | str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        return self.events.record_and_apply(
            user_id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload,
        )

    def _one(self, statement) -> dict[str, Any] | None:
        row = self._session.execute(statement).mappings().first()
        return dict(row) if row is not None else None


__all__ = ["SqlAlchemyInterviewRepository"]

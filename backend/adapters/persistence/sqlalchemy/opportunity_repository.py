from __future__ import annotations

from typing import Any

from sqlalchemy import case, insert, select
from sqlalchemy.orm import Session

from .career_models import action_items
from .core_models import job_applications, job_matches, resumes
from .training_models import interview_sessions


class SqlAlchemyOpportunityWorkspaceRepository:
    def __init__(self, session: Session):
        self._session = session

    def snapshot(
        self,
        user_id: int,
        *,
        opportunity_id: int,
        resume_id: int | None,
    ) -> dict[str, Any]:
        return {
            "resume": self._resume(user_id, resume_id),
            "matches": self._matches(user_id, opportunity_id),
            "interviews": self._interviews(user_id, opportunity_id),
            "actions": self._actions(user_id, opportunity_id),
        }

    def owned_active_exists(self, opportunity_id: int, user_id: int) -> bool:
        statement = select(job_applications.c.id).where(
            job_applications.c.id == opportunity_id,
            job_applications.c.user_id == user_id,
            job_applications.c.deleted_at.is_(None),
        )
        return self._session.execute(statement).first() is not None

    def add_match(
        self,
        user_id: int,
        *,
        resume_id: int,
        job_title: str,
        match_score: int,
        analysis: str,
        jd_text: str,
        details_json: str,
        application_id: int | None,
    ) -> int:
        result = self._session.execute(
            insert(job_matches).values(
                user_id=user_id,
                resume_id=resume_id,
                job_title=job_title,
                match_score=match_score,
                analysis=analysis,
                jd_text=jd_text,
                details_json=details_json,
                application_id=application_id,
            )
        )
        return int(result.inserted_primary_key[0])

    def _resume(self, user_id: int, resume_id: int | None) -> dict[str, Any] | None:
        if resume_id is None:
            return None
        statement = select(
            resumes.c.id,
            resumes.c.title,
            resumes.c.file_path,
            resumes.c.file_type,
            resumes.c.status,
            resumes.c.version_label,
            resumes.c.target_job_title,
            resumes.c.created_at,
            resumes.c.updated_at,
        ).where(resumes.c.id == resume_id, resumes.c.user_id == user_id)
        row = self._session.execute(statement).mappings().first()
        return dict(row) if row is not None else None

    def _matches(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        statement = (
            select(
                job_matches.c.id,
                job_matches.c.resume_id,
                job_matches.c.job_title,
                job_matches.c.match_score,
                job_matches.c.analysis,
                job_matches.c.details_json,
                job_matches.c.created_at,
                resumes.c.title.label("resume_title"),
            )
            .join(
                resumes,
                (resumes.c.id == job_matches.c.resume_id)
                & (resumes.c.user_id == job_matches.c.user_id),
            )
            .where(
                job_matches.c.user_id == user_id,
                job_matches.c.application_id == opportunity_id,
            )
            .order_by(job_matches.c.created_at.desc(), job_matches.c.id.desc())
            .limit(5)
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    def _interviews(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        statement = (
            select(
                interview_sessions.c.id,
                interview_sessions.c.resume_id,
                interview_sessions.c.job_title,
                interview_sessions.c.mode,
                interview_sessions.c.status,
                interview_sessions.c.current_stage,
                interview_sessions.c.score,
                interview_sessions.c.feedback,
                interview_sessions.c.started_at,
                interview_sessions.c.completed_at,
                interview_sessions.c.updated_at,
            )
            .where(
                interview_sessions.c.user_id == user_id,
                interview_sessions.c.application_id == opportunity_id,
            )
            .order_by(interview_sessions.c.started_at.desc(), interview_sessions.c.id.desc())
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    def _actions(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        status_order = case(
            (action_items.c.status == "pending", 0),
            (action_items.c.status == "in_progress", 1),
            else_=2,
        )
        statement = (
            select(
                action_items.c.id,
                action_items.c.title,
                action_items.c.action_type,
                action_items.c.description,
                action_items.c.status,
                action_items.c.priority,
                action_items.c.due_at,
                action_items.c.completed_at,
                action_items.c.created_at,
                action_items.c.updated_at,
            )
            .where(
                action_items.c.user_id == user_id,
                action_items.c.application_id == opportunity_id,
            )
            .order_by(status_order, action_items.c.due_at, action_items.c.id)
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

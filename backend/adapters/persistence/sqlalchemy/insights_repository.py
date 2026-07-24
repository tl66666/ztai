from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .core_models import job_applications, job_matches, resumes
from .training_models import audio_records, interviews, practice_records


class SqlAlchemyCareerInsightsRepository:
    def __init__(self, session: Session):
        self._session = session

    def dashboard_evidence(self, user_id: int) -> dict[str, Any]:
        return {
            "resume_count": self._count(resumes, user_id),
            "interviews": self._rows(
                select(interviews.c.score, interviews.c.created_at)
                .where(interviews.c.user_id == user_id)
                .order_by(interviews.c.created_at)
            ),
            "matches": self._rows(
                select(job_matches.c.match_score, job_matches.c.created_at)
                .where(job_matches.c.user_id == user_id)
                .order_by(job_matches.c.created_at)
            ),
            "applications": self._rows(
                select(
                    job_applications.c.status,
                    job_applications.c.company,
                    job_applications.c.job_title,
                    job_applications.c.updated_at,
                )
                .where(
                    job_applications.c.user_id == user_id,
                    job_applications.c.deleted_at.is_(None),
                )
                .order_by(job_applications.c.updated_at.desc())
            ),
            "practice_count": self._count(practice_records, user_id),
            "audio_count": self._count(audio_records, user_id),
        }

    def report_evidence(self, user_id: int) -> dict[str, Any]:
        return {
            "resumes": self._rows(
                select(resumes.c.title, resumes.c.content, resumes.c.updated_at)
                .where(resumes.c.user_id == user_id)
                .order_by(resumes.c.updated_at.desc())
                .limit(3)
            ),
            "matches": self._rows(
                select(
                    job_matches.c.job_title,
                    job_matches.c.match_score,
                    job_matches.c.created_at,
                )
                .where(job_matches.c.user_id == user_id)
                .order_by(job_matches.c.created_at.desc())
                .limit(5)
            ),
            "interviews": self._rows(
                select(
                    interviews.c.job_title,
                    interviews.c.score,
                    interviews.c.feedback,
                    interviews.c.created_at,
                )
                .where(interviews.c.user_id == user_id)
                .order_by(interviews.c.created_at.desc())
                .limit(5)
            ),
            "applications": self._rows(
                select(
                    job_applications.c.company,
                    job_applications.c.job_title,
                    job_applications.c.status,
                    job_applications.c.city,
                    job_applications.c.notes,
                )
                .where(
                    job_applications.c.user_id == user_id,
                    job_applications.c.deleted_at.is_(None),
                )
                .order_by(job_applications.c.updated_at.desc())
                .limit(8)
            ),
        }

    def coaching_evidence(self, user_id: int) -> dict[str, Any]:
        resume = self._session.execute(
            select(resumes.c.title, resumes.c.content)
            .where(resumes.c.user_id == user_id)
            .order_by(resumes.c.updated_at.desc())
            .limit(1)
        ).mappings().first()
        interview = self._session.execute(
            select(interviews.c.job_title, interviews.c.score, interviews.c.feedback)
            .where(interviews.c.user_id == user_id)
            .order_by(interviews.c.created_at.desc())
            .limit(1)
        ).mappings().first()
        return {
            "resume": dict(resume) if resume is not None else None,
            "interview": dict(interview) if interview is not None else None,
        }

    def _count(self, table, user_id: int) -> int:
        statement = select(func.count()).select_from(table).where(table.c.user_id == user_id)
        return int(self._session.execute(statement).scalar_one())

    def _rows(self, statement) -> list[dict[str, Any]]:
        return [dict(row) for row in self._session.execute(statement).mappings()]

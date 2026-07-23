from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from .core_models import resumes


class SqlAlchemyResumeRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(
        self,
        user_id: int,
        *,
        title: str,
        content: str,
        file_path: str | None = None,
        file_type: str | None = None,
        analysis_result: str | None = None,
        tailored_result: str | None = None,
    ) -> int:
        statement = insert(resumes).values(
            user_id=user_id,
            title=title,
            content=content,
            file_path=file_path,
            file_type=file_type,
            analysis_result=analysis_result,
            tailored_result=tailored_result,
        )
        result = self._session.execute(statement)
        return int(result.inserted_primary_key[0])

    def list_owned(self, user_id: int) -> list[dict[str, Any]]:
        statement = (
            select(resumes)
            .where(resumes.c.user_id == user_id)
            .order_by(resumes.c.updated_at.desc())
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    def get_owned(self, resume_id: int, user_id: int) -> dict[str, Any] | None:
        statement = select(resumes).where(
            resumes.c.id == resume_id,
            resumes.c.user_id == user_id,
        )
        row = self._session.execute(statement).mappings().first()
        return dict(row) if row is not None else None

    def replace_upload(
        self,
        resume_id: int,
        user_id: int,
        *,
        file_path: str,
        file_type: str,
        content: str,
    ) -> bool:
        statement = (
            update(resumes)
            .where(resumes.c.id == resume_id, resumes.c.user_id == user_id)
            .values(
                file_path=file_path,
                file_type=file_type,
                content=content,
                updated_at=func.current_timestamp(),
            )
        )
        return self._session.execute(statement).rowcount > 0

    def update_text(
        self,
        resume_id: int,
        user_id: int,
        *,
        title: str,
        content: str,
    ) -> bool:
        statement = (
            update(resumes)
            .where(resumes.c.id == resume_id, resumes.c.user_id == user_id)
            .values(
                title=title,
                content=content,
                updated_at=func.current_timestamp(),
            )
        )
        return self._session.execute(statement).rowcount > 0

    def delete_owned(self, resume_id: int, user_id: int) -> bool:
        statement = delete(resumes).where(
            resumes.c.id == resume_id,
            resumes.c.user_id == user_id,
        )
        return self._session.execute(statement).rowcount > 0

    def set_analysis(self, resume_id: int, user_id: int, analysis: str) -> bool:
        statement = (
            update(resumes)
            .where(resumes.c.id == resume_id, resumes.c.user_id == user_id)
            .values(analysis_result=analysis)
        )
        return self._session.execute(statement).rowcount > 0

    def set_tailored(self, resume_id: int, user_id: int, tailored: str) -> bool:
        statement = (
            update(resumes)
            .where(resumes.c.id == resume_id, resumes.c.user_id == user_id)
            .values(tailored_result=tailored)
        )
        return self._session.execute(statement).rowcount > 0

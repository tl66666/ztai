from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select

from .agent_session import AgentSessionProvider
from .core_models import resumes


class SqlAlchemyAgentToolStore:
    """Read adapter for agent tools that inspect resume content."""

    def __init__(self, sessions: AgentSessionProvider):
        self.sessions = sessions

    def list_resumes(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        resumes.c.id,
                        resumes.c.user_id,
                        resumes.c.title,
                        func.substr(resumes.c.content, 1, 180).label("preview"),
                        resumes.c.updated_at,
                    )
                    .where(resumes.c.user_id == user_id)
                    .order_by(resumes.c.updated_at.desc())
                    .limit(10)
                ).mappings()
            )

    def get_resume(
        self,
        user_id: int,
        resume_id: int | None,
    ) -> Mapping[str, Any] | None:
        statement = select(
            resumes.c.id,
            resumes.c.user_id,
            resumes.c.title,
            resumes.c.content,
            resumes.c.updated_at,
        ).where(resumes.c.user_id == user_id)
        if resume_id is None:
            statement = statement.order_by(resumes.c.updated_at.desc()).limit(1)
        else:
            statement = statement.where(resumes.c.id == resume_id)
        with self.sessions.session() as session:
            return session.execute(statement).mappings().first()

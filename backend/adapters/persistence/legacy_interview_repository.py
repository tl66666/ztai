from __future__ import annotations

from .sqlalchemy.interview_repository import SqlAlchemyInterviewRepository


class LegacySqliteInterviewRepository(SqlAlchemyInterviewRepository):
    """Offline SQLite adapter retaining the legacy single-writer guarantee."""

    def begin_write(self) -> None:
        self._session.connection().exec_driver_sql("BEGIN IMMEDIATE")


__all__ = ["LegacySqliteInterviewRepository"]

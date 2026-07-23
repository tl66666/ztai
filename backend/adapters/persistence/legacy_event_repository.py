from __future__ import annotations

from typing import Any

from sqlalchemy.dialects import sqlite

from .sqlalchemy.event_repository import SqlAlchemyEventRepository


class LegacySqliteEventRepository(SqlAlchemyEventRepository):
    """Offline compatibility adapter for callers that still own a sqlite3 connection."""

    def __init__(self, connection: Any):
        self._connection = connection

    def _execute(self, statement):
        compiled = statement.compile(
            dialect=sqlite.dialect(paramstyle="qmark"),
            compile_kwargs={"render_postcompile": True},
        )
        parameters = tuple(compiled.params[name] for name in compiled.positiontup or ())
        return self._connection.execute(str(compiled), parameters)


__all__ = ["LegacySqliteEventRepository"]

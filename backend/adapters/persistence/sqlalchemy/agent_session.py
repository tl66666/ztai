from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeAlias

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.database import create_database_engine, sqlite_database_url

SessionFactory: TypeAlias = sessionmaker[Session]


class AgentSessionProvider:
    """Own the transaction seam used by the agent runtime.

    A caller may inject the application's session factory. The path form remains
    available for isolated tests and old local callers while still using the
    same SQLAlchemy transaction semantics.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        session_factory: SessionFactory | None = None,
    ):
        if session_factory is None and db_path is None:
            raise ValueError("db_path or session_factory is required")
        self._engine: Engine | None = None
        if session_factory is None:
            self._engine = create_database_engine(sqlite_database_url(db_path))
            session_factory = sessionmaker(
                bind=self._engine,
                class_=Session,
                expire_on_commit=False,
                autoflush=False,
            )
        self.session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            if self._engine is not None:
                self._engine.dispose()

    @property
    def dialect_name(self) -> str:
        bind = self.session_factory.kw.get("bind")
        if bind is None:
            with self.session_factory() as session:
                bind = session.get_bind()
        return bind.dialect.name

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

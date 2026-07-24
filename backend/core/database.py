from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, MetaData, Table, create_engine, event, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from alembic import command


def sqlite_database_url(db_path: str | Path) -> str:
    """Return a SQLAlchemy URL without relying on platform-specific path syntax."""
    absolute_path = Path(db_path).expanduser().resolve()
    return URL.create("sqlite+pysqlite", database=str(absolute_path)).render_as_string(
        hide_password=False
    )


def resolve_database_url(database_url: str | None, db_path: str | Path) -> str:
    return database_url.strip() if database_url and database_url.strip() else sqlite_database_url(
        db_path
    )


def is_sqlite_url(database_url: str) -> bool:
    return make_url(database_url).get_backend_name() == "sqlite"


def create_database_engine(database_url: str) -> Engine:
    """Build the synchronous engine used by repositories and migrations."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        engine = create_engine(
            url,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA busy_timeout = 30000")
            cursor.close()

        return engine

    return create_engine(
        url,
        future=True,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


class Database:
    """Deep persistence module: engine, transactions, migrations, and readiness."""

    def __init__(self, database_url: str):
        self.url = make_url(database_url)
        self.engine = create_database_engine(database_url)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )

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

    def upgrade(self) -> None:
        config = Config(str(_project_root() / "alembic.ini"))
        config.set_main_option("script_location", str(_project_root() / "alembic"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                tables = set(inspect(connection).get_table_names())
                if "alembic_version" not in tables:
                    return False
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
                connection.execute(text("SELECT 1")).scalar_one()
        except Exception:
            return False
        return revision == self.head_revision()

    def ensure_local_user(self, user_id: int) -> None:
        """Repair old installations that contain a legacy users table."""
        local_id = int(user_id)
        if local_id <= 0:
            raise ValueError("local user id must be positive")
        if "users" not in inspect(self.engine).get_table_names():
            return

        users = Table("users", MetaData(), autoload_with=self.engine)
        required = {"id", "username", "password"}
        if not required.issubset(users.c.keys()):
            return
        with self.engine.connect() as connection:
            if connection.execute(
                select(users.c.id).where(users.c.id == local_id)
            ).first():
                return

        for suffix in range(100):
            values = {
                "id": local_id,
                "username": (
                    f"local-user-{local_id}"
                    if suffix == 0
                    else f"local-user-{local_id}-{suffix}"
                ),
                "password": "local-only",
            }
            if "email" in users.c:
                values["email"] = ""
            try:
                with self.engine.begin() as connection:
                    connection.execute(users.insert().values(**values))
                return
            except IntegrityError:
                continue
        raise RuntimeError("unable to initialize the local user record")

    @staticmethod
    def head_revision() -> str:
        config = Config(str(_project_root() / "alembic.ini"))
        config.set_main_option("script_location", str(_project_root() / "alembic"))
        script = ScriptDirectory.from_config(config)
        return script.get_current_head()

    def dispose(self) -> None:
        self.engine.dispose()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

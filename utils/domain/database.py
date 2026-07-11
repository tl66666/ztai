from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
import tempfile


APPLICATION_STATUSES = (
    "意向",
    "准备中",
    "已投递",
    "简历筛选",
    "笔试",
    "一面",
    "二面",
    "HR 面",
    "Offer",
    "已拒绝",
    "已结束",
)

LEGACY_STATUS_MAP = {
    "面试中": "一面",
    "面试": "一面",
    "筛选中": "简历筛选",
    "已录用": "Offer",
    "拒绝": "已拒绝",
}

SCHEMA_VERSION = 1
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db_path: str | os.PathLike[str]) -> sqlite3.Connection:
    conn = sqlite3.connect(os.fspath(db_path), factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    column_type: str,
) -> None:
    if not _IDENTIFIER.fullmatch(table) or not _IDENTIFIER.fullmatch(column):
        raise ValueError("table and column must be valid SQL identifiers")

    columns = {
        row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    if column not in columns:
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {column_type}')


def migrate_database(db_path: str | os.PathLike[str]) -> None:
    path = os.fspath(db_path)
    if _is_in_memory_database(path):
        raise ValueError(
            "migrate_database requires a persistent path, not an in-memory database"
        )

    with connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            current_version = conn.execute("PRAGMA user_version").fetchone()[0]
            if current_version >= SCHEMA_VERSION:
                conn.rollback()
                return

            # The reserved lock prevents new writes while a separate reader snapshots WAL.
            _backup_pre_migration_database(path)
            if current_version < 1:
                _migrate_to_version_1(conn)
                conn.execute("PRAGMA user_version = 1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _backup_pre_migration_database(db_path: str) -> None:
    if not os.path.isfile(db_path) or os.path.getsize(db_path) == 0:
        return
    if _is_obvious_temporary_database(db_path):
        return

    backup_path = f"{db_path}.backup-v0"
    if os.path.exists(backup_path):
        return

    backup_dir = os.path.dirname(os.path.abspath(backup_path))
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=backup_dir,
        prefix=f".{os.path.basename(backup_path)}-",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    try:
        with connect(db_path) as source, connect(temporary_path) as destination:
            source.backup(destination)
        os.replace(temporary_path, backup_path)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def _is_in_memory_database(db_path: str) -> bool:
    return db_path == ":memory:" or db_path.startswith("file::memory:")


def _is_obvious_temporary_database(db_path: str) -> bool:
    if _is_in_memory_database(db_path):
        return True

    resolved_path = Path(db_path).resolve()
    temp_roots = {Path(tempfile.gettempdir()).resolve()}
    for env_name in ("TMP", "TEMP", "TMPDIR"):
        value = os.environ.get(env_name)
        if value:
            temp_roots.add(Path(value).resolve())

    return any(resolved_path == root or root in resolved_path.parents for root in temp_roots)


def _migrate_to_version_1(conn: sqlite3.Connection) -> None:
    _create_legacy_base_tables_if_missing(conn)

    approved_columns = {
        "resumes": (
            ("parent_resume_id", "INTEGER REFERENCES resumes(id)"),
            ("version_label", "TEXT"),
            ("target_job_title", "TEXT"),
            ("application_id", "INTEGER REFERENCES job_applications(id)"),
            ("status", "TEXT DEFAULT 'active'"),
            ("source_type", "TEXT DEFAULT 'manual'"),
        ),
        "job_applications": (
            ("jd_text", "TEXT"),
            ("source_url", "TEXT"),
            ("channel", "TEXT"),
            ("resume_id", "INTEGER REFERENCES resumes(id)"),
            ("priority", "INTEGER DEFAULT 0"),
            ("contact_name", "TEXT"),
            ("contact_info", "TEXT"),
            ("next_action_at", "TEXT"),
            ("interview_at", "TEXT"),
            ("deadline_at", "TEXT"),
            ("rejection_reason", "TEXT"),
            ("offer_details", "TEXT"),
            ("created_by", "TEXT DEFAULT 'user'"),
        ),
        "job_matches": (
            ("application_id", "INTEGER REFERENCES job_applications(id)"),
            ("jd_text", "TEXT"),
            ("details_json", "TEXT"),
        ),
    }
    for table, columns in approved_columns.items():
        for column, column_type in columns:
            ensure_column(conn, table, column, column_type)

    for legacy_status, canonical_status in LEGACY_STATUS_MAP.items():
        conn.execute(
            "UPDATE job_applications SET status = ? WHERE status = ?",
            (canonical_status, legacy_status),
        )

    _create_domain_tables(conn)
    _create_domain_indexes(conn)


def _create_legacy_base_tables_if_missing(conn: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            status TEXT DEFAULT '已投递',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    for statement in statements:
        conn.execute(statement)


def _create_domain_tables(conn: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE IF NOT EXISTS career_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            headline TEXT,
            summary TEXT,
            target_roles_json TEXT,
            skills_json TEXT,
            preferences_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS action_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            application_id INTEGER REFERENCES job_applications(id),
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            due_at TEXT,
            completed_at TEXT,
            source TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS domain_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            aggregate_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT,
            occurred_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS career_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            title TEXT,
            period_start TEXT,
            period_end TEXT,
            content_json TEXT NOT NULL,
            status TEXT DEFAULT 'ready',
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            application_id INTEGER REFERENCES job_applications(id),
            resume_id INTEGER REFERENCES resumes(id),
            job_title TEXT NOT NULL,
            mode TEXT,
            status TEXT DEFAULT 'active',
            current_stage TEXT,
            conversation_json TEXT,
            score INTEGER,
            feedback TEXT,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_action_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_run_id TEXT,
            action_type TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            payload_json TEXT NOT NULL,
            rationale TEXT,
            status TEXT DEFAULT 'pending',
            risk_level TEXT DEFAULT 'low',
            reviewed_by TEXT,
            reviewed_at TEXT,
            executed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    for statement in statements:
        conn.execute(statement)


def _create_domain_indexes(conn: sqlite3.Connection) -> None:
    statements = (
        "CREATE INDEX IF NOT EXISTS idx_resumes_application ON resumes(application_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_user_status ON job_applications(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_applications_next_action ON job_applications(next_action_at)",
        "CREATE INDEX IF NOT EXISTS idx_job_matches_application ON job_matches(application_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_career_profiles_user ON career_profiles(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_action_items_user_status_due ON action_items(user_id, status, due_at)",
        "CREATE INDEX IF NOT EXISTS idx_action_items_application ON action_items(application_id)",
        "CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_domain_events_user ON domain_events(user_id, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_career_reports_user_type ON career_reports(user_id, report_type, generated_at)",
        "CREATE INDEX IF NOT EXISTS idx_interview_sessions_application ON interview_sessions(application_id)",
        "CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_status ON interview_sessions(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_agent_proposals_user_status ON agent_action_proposals(user_id, status, created_at)",
    )
    for statement in statements:
        conn.execute(statement)

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

SCHEMA_VERSION = 4
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
        try:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {column_type}')
        except sqlite3.OperationalError as exc:
            refreshed = {
                row[1]
                for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            }
            if column not in refreshed or "duplicate column name" not in str(exc).lower():
                raise


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
            _backup_pre_migration_database(path, current_version)
            if current_version < 1:
                _migrate_to_version_1(conn)
                conn.execute("PRAGMA user_version = 1")
            if current_version < 2:
                _migrate_to_version_2(conn)
                conn.execute("PRAGMA user_version = 2")
            if current_version < 3:
                _migrate_to_version_3(conn)
                conn.execute("PRAGMA user_version = 3")
            if current_version < 4:
                _migrate_to_version_4(conn)
                conn.execute("PRAGMA user_version = 4")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _backup_pre_migration_database(db_path: str, current_version: int) -> None:
    if not os.path.isfile(db_path) or os.path.getsize(db_path) == 0:
        return
    if _is_obvious_temporary_database(db_path):
        return

    backup_path = f"{db_path}.backup-v{current_version}"
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


def _migrate_to_version_2(conn: sqlite3.Connection) -> None:
    evidence_indexes = (
        ("job_matches", "idx_job_matches_user_created"),
        ("interviews", "idx_interviews_user_created"),
        ("practice_records", "idx_practice_records_user_created"),
        ("audio_records", "idx_audio_records_user_created"),
    )
    for table, index_name in evidence_indexes:
        if _table_exists(conn, table):
            ensure_column(conn, table, "created_at", "TEXT")
        if table == "interviews" and _table_exists(conn, table):
            ensure_column(conn, table, "source_session_id", "TEXT")
        columns = _table_columns(conn, table)
        if {"user_id", "created_at"}.issubset(columns):
            conn.execute(
                f'CREATE INDEX IF NOT EXISTS "{index_name}" '
                f'ON "{table}"(user_id, created_at)'
            )


def _migrate_to_version_3(conn: sqlite3.Connection) -> None:
    opportunity_columns = (
        ("city", "TEXT"),
        ("salary_min", "INTEGER"),
        ("salary_max", "INTEGER"),
        ("notes", "TEXT"),
        ("applied_at", "TEXT"),
        ("updated_at", "TEXT"),
        ("deleted_at", "TEXT"),
    )
    if _table_exists(conn, "job_applications"):
        for column, column_type in opportunity_columns:
            ensure_column(conn, "job_applications", column, column_type)
    if not _table_exists(conn, "agent_action_proposals"):
        _create_domain_tables(conn)
    columns = (
        ("arguments_json", "TEXT"),
        ("preview", "TEXT"),
        ("expires_at", "TEXT"),
        ("idempotency_key", "TEXT"),
        ("result_json", "TEXT"),
        ("error_code", "TEXT"),
        ("executing_at", "TEXT"),
        ("completed_at", "TEXT"),
        ("cancelled_at", "TEXT"),
        ("failed_at", "TEXT"),
        ("expired_at", "TEXT"),
    )
    for column, column_type in columns:
        ensure_column(conn, "agent_action_proposals", column, column_type)
    conn.execute(
        """
        UPDATE agent_action_proposals
        SET arguments_json = COALESCE(arguments_json, payload_json, '{}')
        WHERE arguments_json IS NULL
        """
    )
    conn.execute(
        """
        UPDATE agent_action_proposals
        SET expires_at = datetime(COALESCE(created_at, CURRENT_TIMESTAMP), '+30 minutes')
        WHERE status = 'pending' AND expires_at IS NULL
        """
    )
    conn.execute(
        """
        UPDATE agent_action_proposals
        SET idempotency_key = lower(hex(randomblob(16)))
        WHERE idempotency_key IS NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_proposals_user_status_expires
        ON agent_action_proposals(user_id, status, expires_at, created_at)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_proposals_user_idempotency
        ON agent_action_proposals(user_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )


def _migrate_to_version_4(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "domain_events", "source", "TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_domain_events_agent_source_receipt
        ON domain_events(user_id, source)
        WHERE source LIKE 'agent:%'
        """
    )


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


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
            source TEXT,
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
            arguments_json TEXT,
            preview TEXT,
            rationale TEXT,
            status TEXT DEFAULT 'pending',
            risk_level TEXT DEFAULT 'low',
            expires_at TEXT,
            idempotency_key TEXT,
            result_json TEXT,
            error_code TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            executing_at TEXT,
            executed_at TEXT,
            completed_at TEXT,
            cancelled_at TEXT,
            failed_at TEXT,
            expired_at TEXT,
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
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_domain_events_agent_source_receipt ON domain_events(user_id, source) WHERE source LIKE 'agent:%'",
        "CREATE INDEX IF NOT EXISTS idx_career_reports_user_type ON career_reports(user_id, report_type, generated_at)",
        "CREATE INDEX IF NOT EXISTS idx_interview_sessions_application ON interview_sessions(application_id)",
        "CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_status ON interview_sessions(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_agent_proposals_user_status ON agent_action_proposals(user_id, status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_agent_proposals_user_status_expires ON agent_action_proposals(user_id, status, expires_at, created_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_proposals_user_idempotency ON agent_action_proposals(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL",
    )
    for statement in statements:
        conn.execute(statement)

import json
import os
import sqlite3
import tempfile
import unittest
import uuid

from utils.domain.database import (
    APPLICATION_STATUSES,
    LEGACY_STATUS_MAP,
    connect,
    migrate_database,
)


EXPECTED_APPLICATION_STATUSES = (
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

REQUIRED_COLUMNS = {
    "resumes": {
        "parent_resume_id",
        "version_label",
        "target_job_title",
        "application_id",
        "status",
        "source_type",
    },
    "job_applications": {
        "jd_text",
        "source_url",
        "channel",
        "resume_id",
        "priority",
        "contact_name",
        "contact_info",
        "next_action_at",
        "interview_at",
        "deadline_at",
        "rejection_reason",
        "offer_details",
        "created_by",
    },
    "job_matches": {"application_id", "jd_text", "details_json"},
}

REQUIRED_TABLES = {
    "career_profiles",
    "action_items",
    "domain_events",
    "career_reports",
    "interview_sessions",
    "agent_action_proposals",
}


def create_legacy_database(db_path):
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE TABLE job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                status TEXT
            );
            CREATE TABLE job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                job_title TEXT NOT NULL
            );
            INSERT INTO job_applications (
                user_id, company, job_title, status
            ) VALUES (1, '示例公司', '测试工程师', '面试中');
            """
        )


class DomainMigrationTests(unittest.TestCase):
    def test_publishes_canonical_application_statuses_and_legacy_map(self):
        self.assertEqual(APPLICATION_STATUSES, EXPECTED_APPLICATION_STATUSES)
        self.assertEqual(LEGACY_STATUS_MAP["面试中"], "一面")
        self.assertEqual(LEGACY_STATUS_MAP["面试"], "一面")
        self.assertEqual(LEGACY_STATUS_MAP["筛选中"], "简历筛选")
        self.assertEqual(LEGACY_STATUS_MAP["已录用"], "Offer")
        self.assertEqual(LEGACY_STATUS_MAP["拒绝"], "已拒绝")

    def test_connect_enables_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with connect(os.path.join(temp_dir, "test.db")) as conn:
                enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]

        self.assertEqual(enabled, 1)

    def test_migrates_legacy_schema_and_data_idempotently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "legacy-test.db")
            create_legacy_database(db_path)

            migrate_database(db_path)
            migrate_database(db_path)

            with connect(db_path) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                status = conn.execute(
                    "SELECT status FROM job_applications WHERE id = 1"
                ).fetchone()[0]
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                columns = {
                    table: {
                        row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')
                    }
                    for table in REQUIRED_COLUMNS
                }

            self.assertEqual(version, 4)
            self.assertEqual(status, "一面")
            self.assertTrue(REQUIRED_TABLES.issubset(tables))
            for table, required in REQUIRED_COLUMNS.items():
                self.assertTrue(required.issubset(columns[table]), table)
            self.assertFalse(os.path.exists(f"{db_path}.backup-v0"))

    def test_first_migration_backs_up_a_persistent_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persistent_dir = os.path.join(os.getcwd(), ".migration-test-data")
            os.makedirs(persistent_dir, exist_ok=True)
            db_path = os.path.join(persistent_dir, f"legacy-{uuid.uuid4().hex}.db")
            backup_path = f"{db_path}.backup-v0"
            try:
                create_legacy_database(db_path)

                migrate_database(db_path)

                self.assertTrue(os.path.exists(backup_path))
                with connect(backup_path) as backup:
                    self.assertEqual(backup.execute("PRAGMA user_version").fetchone()[0], 0)
                    self.assertEqual(
                        backup.execute(
                            "SELECT status FROM job_applications WHERE id = 1"
                        ).fetchone()[0],
                        "面试中",
                    )
            finally:
                for path in (backup_path, db_path):
                    if os.path.exists(path):
                        os.remove(path)
                if os.path.isdir(persistent_dir):
                    os.rmdir(persistent_dir)

    def test_backup_includes_committed_wal_state_while_connection_is_open(self):
        persistent_dir = os.path.join(
            os.getcwd(), f".migration-wal-test-{uuid.uuid4().hex}"
        )
        os.makedirs(persistent_dir)
        db_path = os.path.join(persistent_dir, "legacy.db")
        backup_path = f"{db_path}.backup-v0"
        writer = sqlite3.connect(db_path)
        try:
            writer.execute("PRAGMA journal_mode = WAL")
            writer.execute("PRAGMA wal_autocheckpoint = 0")
            writer.executescript(
                """
                CREATE TABLE job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    company TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    status TEXT
                );
                INSERT INTO job_applications (
                    user_id, company, job_title, status
                ) VALUES (1, 'WAL 公司', '后端工程师', '面试中');
                """
            )
            writer.commit()

            migrate_database(db_path)

            with connect(backup_path) as backup:
                row = backup.execute(
                    "SELECT company, status FROM job_applications WHERE id = 1"
                ).fetchone()
                self.assertEqual(tuple(row), ("WAL 公司", "面试中"))
                version = backup.execute("PRAGMA user_version").fetchone()[0]
                self.assertEqual(version, 0)
        finally:
            writer.close()
            for suffix in ("-shm", "-wal", ".backup-v0", ""):
                path = f"{db_path}{suffix}"
                if os.path.exists(path):
                    os.remove(path)
            os.rmdir(persistent_dir)

    def test_in_memory_database_requires_a_persistent_path(self):
        with self.assertRaisesRegex(ValueError, "persistent path"):
            migrate_database(":memory:")

    def test_failed_migration_does_not_advance_user_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "broken-test.db")
            create_legacy_database(db_path)
            with connect(db_path) as conn:
                conn.execute("CREATE TABLE career_profiles (id INTEGER PRIMARY KEY)")

            with self.assertRaises(sqlite3.OperationalError):
                migrate_database(db_path)

            with connect(db_path) as conn:
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_version_one_migrates_to_evidence_indexes_idempotently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "version-one.db")
            with connect(db_path) as conn:
                conn.executescript(
                    """
                    CREATE TABLE job_matches (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                        resume_id INTEGER NOT NULL, job_title TEXT NOT NULL,
                        created_at TEXT
                    );
                    CREATE TABLE interviews (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                        job_title TEXT NOT NULL, created_at TEXT
                    );
                    CREATE TABLE practice_records (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT
                    );
                    CREATE TABLE audio_records (
                        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT
                    );
                    PRAGMA user_version = 1;
                    """
                )

            migrate_database(db_path)
            migrate_database(db_path)

            with connect(db_path) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                interview_columns = {
                    row[1] for row in conn.execute('PRAGMA table_info("interviews")')
                }
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'index'"
                    )
                }

            self.assertEqual(version, 4)
            self.assertIn("source_session_id", interview_columns)
            self.assertTrue(
                {
                    "idx_job_matches_user_created",
                    "idx_interviews_user_created",
                    "idx_practice_records_user_created",
                    "idx_audio_records_user_created",
                }.issubset(indexes)
            )

    def test_version_two_migrates_agent_proposals_to_version_three_idempotently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "version-two.db")
            create_legacy_database(db_path)
            migrate_database(db_path)
            with connect(db_path) as conn:
                conn.execute("PRAGMA user_version = 2")
                conn.execute(
                    """
                    INSERT INTO agent_action_proposals (
                        user_id, action_type, payload_json, status
                    ) VALUES (1, 'create_action_item', '{"title":"Legacy"}', 'pending')
                    """
                )

            migrate_database(db_path)
            migrate_database(db_path)

            with connect(db_path) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                columns = {
                    row[1]
                    for row in conn.execute(
                        'PRAGMA table_info("agent_action_proposals")'
                    )
                }
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'index'"
                    )
                }
                legacy = conn.execute(
                    """
                    SELECT arguments_json, expires_at, idempotency_key
                    FROM agent_action_proposals
                    WHERE action_type = 'create_action_item'
                    """
                ).fetchone()

            self.assertEqual(version, 4)
            self.assertTrue(
                {
                    "arguments_json",
                    "preview",
                    "expires_at",
                    "idempotency_key",
                    "result_json",
                    "error_code",
                    "executing_at",
                    "completed_at",
                    "cancelled_at",
                    "failed_at",
                    "expired_at",
                }.issubset(columns)
            )
            self.assertTrue(
                {
                    "idx_agent_proposals_user_status_expires",
                    "idx_agent_proposals_user_idempotency",
                }.issubset(indexes)
            )
            self.assertEqual(json.loads(legacy["arguments_json"]), {"title": "Legacy"})
            self.assertIsNotNone(legacy["expires_at"])
            self.assertIsNotNone(legacy["idempotency_key"])

    def test_version_three_adds_unique_agent_domain_event_receipts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "version-three.db")
            create_legacy_database(db_path)
            migrate_database(db_path)
            with connect(db_path) as conn:
                conn.execute("PRAGMA user_version = 3")

            migrate_database(db_path)
            migrate_database(db_path)

            with connect(db_path) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                columns = {
                    row[1]
                    for row in conn.execute('PRAGMA table_info("domain_events")')
                }
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'index'"
                    )
                }
                event_values = (
                    1,
                    "action_item",
                    "1",
                    "action_item.created",
                    "{}",
                    "agent:receipt:create_action_item",
                )
                conn.execute(
                    """
                    INSERT INTO domain_events (
                        user_id, aggregate_type, aggregate_id, event_type,
                        payload_json, source
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    event_values,
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        """
                        INSERT INTO domain_events (
                            user_id, aggregate_type, aggregate_id, event_type,
                            payload_json, source
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        event_values,
                    )

            self.assertEqual(version, 4)
            self.assertIn("source", columns)
            self.assertIn("idx_domain_events_agent_source_receipt", indexes)


if __name__ == "__main__":
    unittest.main()

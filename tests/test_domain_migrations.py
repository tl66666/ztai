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

            self.assertEqual(version, 1)
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


if __name__ == "__main__":
    unittest.main()

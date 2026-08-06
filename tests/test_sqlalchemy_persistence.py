from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.adapters.persistence.sqlalchemy import (
    SqlAlchemyUnitOfWork,
    audio_records,
    interviews,
    job_applications,
    metadata,
    practice_records,
)
from backend.core.database import Database, sqlite_database_url
from backend.core.runtime import RuntimeDatabase


class SqlAlchemyPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary_directory.name)
        self.db_path = self.root / "jobhunter.db"
        self.database = Database(sqlite_database_url(self.db_path))
        self.database.upgrade()
        self.unit_of_work = lambda: SqlAlchemyUnitOfWork(
            self.database.session_factory
        )

    def tearDown(self) -> None:
        self.database.dispose()
        import gc, shutil
        gc.collect()
        try:
            self.temporary_directory.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temporary_directory.name, ignore_errors=True)
    def test_alembic_baseline_creates_complete_empty_sqlite_schema(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()[0]

        self.assertEqual(revision, "20260724_02")
        self.assertTrue(
            {
                "resumes",
                "job_applications",
                "job_matches",
                "interviews",
                "practice_records",
                "audio_records",
                "career_profiles",
                "action_items",
                "domain_events",
                "career_reports",
                "interview_sessions",
                "agent_action_proposals",
                "agent_conversations",
                "agent_messages",
                "agent_tasks",
                "agent_memories",
                "agent_runs",
                "agent_memories_fts",
                "background_jobs",
            }.issubset(tables)
        )
        self.assertTrue(self.database.is_ready())

    def test_repository_contract_enforces_owner_conditions(self) -> None:
        with self.unit_of_work() as unit_of_work:
            owner_resume_id = unit_of_work.resumes.add(
                1,
                title="Owner",
                content="owner content",
            )
            foreign_resume_id = unit_of_work.resumes.add(
                2,
                title="Private",
                content="private content",
            )
        with self.database.session() as session:
            opportunity_id = int(
                session.execute(
                    insert(job_applications).values(
                        user_id=1,
                        company="Example",
                        job_title="Engineer",
                    )
                ).inserted_primary_key[0]
            )
            foreign_opportunity_id = int(
                session.execute(
                    insert(job_applications).values(
                        user_id=2,
                        company="Private",
                        job_title="Engineer",
                    )
                ).inserted_primary_key[0]
            )

        with self.unit_of_work() as unit_of_work:
            self.assertEqual(
                [row["id"] for row in unit_of_work.resumes.list_owned(1)],
                [owner_resume_id],
            )
            self.assertIsNone(
                unit_of_work.resumes.get_owned(foreign_resume_id, 1)
            )
            self.assertFalse(
                unit_of_work.resumes.set_analysis(
                    foreign_resume_id,
                    1,
                    "must-not-write",
                )
            )
            self.assertTrue(
                unit_of_work.agent_context.context_entities_exist(
                    1,
                    resume_id=owner_resume_id,
                    opportunity_id=opportunity_id,
                )
            )
            self.assertFalse(
                unit_of_work.agent_context.context_entities_exist(
                    1,
                    opportunity_id=foreign_opportunity_id,
                )
            )

    def test_schema_compiles_for_postgresql(self) -> None:
        dialect = postgresql.dialect()

        for table in metadata.sorted_tables:
            self.assertTrue(str(CreateTable(table).compile(dialect=dialect)))
            for index in table.indexes:
                self.assertTrue(str(CreateIndex(index).compile(dialect=dialect)))

    def test_training_repository_preserves_history_contract(self) -> None:
        with self.database.session() as session:
            session.execute(
                insert(interviews).values(
                    user_id=1,
                    job_title="工程师",
                    score=88,
                )
            )
            session.execute(
                insert(interviews).values(
                    user_id=2,
                    job_title="私有",
                    score=99,
                )
            )
        with self.unit_of_work() as unit_of_work:
            unit_of_work.training.save_practice(
                1,
                category="python",
                question="Q",
                answer="A",
                score=90,
                feedback={"ok": True},
            )
            unit_of_work.training.save_audio(
                1,
                transcript="回答",
                audio_file="sample.webm",
                score=80,
                metrics={"silence": 0.1},
                feedback={"summary": "ok"},
            )
        with self.unit_of_work() as unit_of_work:
            records = unit_of_work.training.list_all(1)
            self.assertEqual(len(records["interviews"]), 1)
            self.assertEqual(len(records["practices"]), 1)
            self.assertEqual(len(records["audios"]), 1)
            self.assertEqual(unit_of_work.training.audio_files(1), ["sample.webm"])
            unit_of_work.training.clear(1)
        with self.database.session() as session:
            self.assertEqual(
                session.execute(
                    practice_records.select().where(
                        practice_records.c.user_id == 1
                    )
                ).all(),
                [],
            )
            self.assertEqual(
                session.execute(
                    audio_records.select().where(audio_records.c.user_id == 1)
                ).all(),
                [],
            )


class LegacyDatabaseAdoptionTests(unittest.TestCase):
    def test_alembic_adopts_version_five_without_losing_rows(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            db_path = root / "legacy.db"
            with sqlite3.connect(db_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    );
                    INSERT INTO users VALUES (2, 'local-user-1', 'legacy');
                    CREATE TABLE resumes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    INSERT INTO resumes(user_id,title,content)
                    VALUES (1,'保留简历','不能丢失');
                    PRAGMA user_version = 5;
                    """
                )

            runtime = RuntimeDatabase(
                db_path,
                upload_folder=root / "uploads",
                export_folder=root / "exports",
                local_user_id=1,
            )
            try:
                runtime.initialize()
                self.assertTrue(runtime.ready())
            finally:
                runtime.close()

            with sqlite3.connect(db_path) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT title, content FROM resumes"
                    ).fetchall(),
                    [("保留简历", "不能丢失")],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT username FROM users WHERE id = 1"
                    ).fetchone()[0],
                    "local-user-1-1",
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT version_num FROM alembic_version"
                    ).fetchone()[0],
                        "20260724_02",
                )


if __name__ == "__main__":
    unittest.main()

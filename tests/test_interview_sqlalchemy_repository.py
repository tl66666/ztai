from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import insert, select

from backend.adapters.persistence.sqlalchemy.career_models import action_items
from backend.adapters.persistence.sqlalchemy.core_models import (
    job_applications,
    resumes,
)
from backend.adapters.persistence.sqlalchemy.interview_repository import (
    SqlAlchemyInterviewRepository,
)
from backend.core.database import Database, sqlite_database_url
from utils.domain.interviews import InterviewService


class TrackingInterviewRepository(SqlAlchemyInterviewRepository):
    created = 0

    def __init__(self, session):
        super().__init__(session)
        type(self).created += 1


class InterviewSqlAlchemyRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "interview.db"
        self.database = Database(sqlite_database_url(self.db_path))
        self.database.upgrade()
        self.database.ensure_local_user(1)
        TrackingInterviewRepository.created = 0

    def tearDown(self):
        self.database.dispose()
        import gc, shutil
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temp_dir.name, ignore_errors=True)
    def test_service_accepts_injected_session_and_repository_factories(self):
        with self.database.session() as session:
            resume_id = session.execute(
                insert(resumes).values(
                    user_id=1,
                    title="Resume",
                    content="Python APIs",
                )
            ).inserted_primary_key[0]

        service = InterviewService(
            session_factory=self.database.session_factory,
            repository_factory=TrackingInterviewRepository,
        )
        started = service.start(
            1,
            int(resume_id),
            "Backend Engineer",
            "Build reliable APIs",
            "standard",
            "tech",
        )
        answered = service.answer(
            1,
            int(started["session_id"]),
            "I designed a reliable API.",
            submission_id="submission-1",
            expected_stage_index=0,
        )

        self.assertGreaterEqual(TrackingInterviewRepository.created, 2)
        self.assertEqual(started["stage"], "opening")
        self.assertEqual(answered["stage"], "resume_deep_dive")
        self.assertEqual(answered["progress"], 2)

    def test_completion_event_updates_only_the_exact_linked_action(self):
        with self.database.session() as session:
            opportunity_id = session.execute(
                insert(job_applications).values(
                    user_id=1,
                    company="Acme",
                    job_title="Engineer",
                )
            ).inserted_primary_key[0]
            exact_action_id = session.execute(
                insert(action_items).values(
                    user_id=1,
                    application_id=opportunity_id,
                    title="Mock interview",
                    action_type="mock_interview",
                    status="pending",
                )
            ).inserted_primary_key[0]
            other_action_id = session.execute(
                insert(action_items).values(
                    user_id=1,
                    application_id=opportunity_id,
                    title="Other mock interview",
                    action_type="mock_interview",
                    status="pending",
                )
            ).inserted_primary_key[0]

        service = InterviewService(
            session_factory=self.database.session_factory,
            repository_factory=SqlAlchemyInterviewRepository,
        )
        started = service.start(
            1,
            None,
            "Engineer",
            "",
            "standard",
            "tech",
            application_id=int(opportunity_id),
            action_id=int(exact_action_id),
        )
        for index in range(5):
            result = service.answer(
                1,
                int(started["session_id"]),
                f"Answer {index}",
            )

        with self.database.session() as session:
            rows = dict(
                session.execute(
                    select(action_items.c.id, action_items.c.status).where(
                        action_items.c.id.in_((exact_action_id, other_action_id))
                    )
                ).all()
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(rows[int(exact_action_id)], "completed")
        self.assertEqual(rows[int(other_action_id)], "pending")


if __name__ == "__main__":
    unittest.main()

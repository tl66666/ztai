from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import update

from backend.adapters.jobs import SqlAlchemyJobQueue, background_jobs
from backend.core.database import Database, sqlite_database_url


class DurableJobQueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Database(
            sqlite_database_url(
                Path(self.temporary_directory.name) / "jobs.db"
            )
        )
        self.database.upgrade()
        self.queue = SqlAlchemyJobQueue(self.database.session_factory)

    def tearDown(self):
        self.database.dispose()
        self.temporary_directory.cleanup()

    def test_submit_is_idempotent_per_owner_and_job_type(self):
        first = self.queue.submit(
            "resume.analyze",
            {"resume_id": 1},
            owner_id=1,
            idempotency_key="request-1",
        )
        duplicate = self.queue.submit(
            "resume.analyze",
            {"resume_id": 2},
            owner_id=1,
            idempotency_key="request-1",
        )
        other_owner = self.queue.submit(
            "resume.analyze",
            {"resume_id": 2},
            owner_id=2,
            idempotency_key="request-1",
        )

        self.assertEqual(first.id, duplicate.id)
        self.assertEqual(duplicate.payload, {"resume_id": 1})
        self.assertNotEqual(first.id, other_owner.id)

    def test_lease_heartbeat_success_and_owner_scoped_status(self):
        submitted = self.queue.submit(
            "test.echo",
            {"value": 1},
            owner_id=1,
        )
        leased = self.queue.lease("worker-1", lease_seconds=30)

        self.assertEqual(leased.id, submitted.id)
        self.assertEqual(leased.status, "running")
        self.assertEqual(leased.attempts, 1)
        self.assertTrue(
            self.queue.heartbeat(
                leased.id,
                "worker-1",
                lease_seconds=30,
            )
        )
        self.assertTrue(
            self.queue.succeed(leased.id, "worker-1", {"value": 2})
        )
        self.assertEqual(
            self.queue.get(leased.id, owner_id=1).result,
            {"value": 2},
        )
        self.assertIsNone(self.queue.get(leased.id, owner_id=2))

    def test_failure_retries_then_becomes_terminal(self):
        submitted = self.queue.submit(
            "test.fail",
            {},
            owner_id=1,
            max_attempts=2,
        )
        first = self.queue.lease("worker-1", lease_seconds=30)
        self.queue.fail(
            first.id,
            "worker-1",
            "first failure",
            retry_delay_seconds=0,
        )
        second = self.queue.lease("worker-2", lease_seconds=30)
        self.queue.fail(
            second.id,
            "worker-2",
            "final failure",
            retry_delay_seconds=0,
        )

        finished = self.queue.get(submitted.id, owner_id=1)
        self.assertEqual(finished.status, "failed")
        self.assertEqual(finished.attempts, 2)
        self.assertEqual(finished.error, "final failure")

    def test_expired_lease_is_recovered_after_worker_restart(self):
        submitted = self.queue.submit(
            "test.recover",
            {},
            owner_id=1,
            max_attempts=2,
        )
        first = self.queue.lease("dead-worker", lease_seconds=30)
        with self.database.session() as session:
            session.execute(
                update(background_jobs)
                .where(background_jobs.c.id == first.id)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )

        restarted_queue = SqlAlchemyJobQueue(self.database.session_factory)
        self.assertEqual(restarted_queue.recover_stale(), 1)
        recovered = restarted_queue.lease("new-worker", lease_seconds=30)
        self.assertEqual(recovered.id, submitted.id)
        self.assertEqual(recovered.attempts, 2)
        with self.database.session() as session:
            session.execute(
                update(background_jobs)
                .where(background_jobs.c.id == recovered.id)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
        self.assertEqual(restarted_queue.recover_stale(), 1)
        self.assertEqual(
            restarted_queue.get(submitted.id, owner_id=1).status,
            "failed",
        )

    def test_cancel_prevents_queued_job_from_running(self):
        submitted = self.queue.submit("test.cancel", {}, owner_id=1)
        cancelled = self.queue.cancel(submitted.id, owner_id=1)

        self.assertEqual(cancelled.status, "cancelled")
        self.assertIsNone(self.queue.lease("worker", lease_seconds=30))


if __name__ == "__main__":
    unittest.main()

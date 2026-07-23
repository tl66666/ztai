from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.ports.job_queue import Job, JobPayload

from .models import background_jobs
from .records import encode_payload, to_job, utc_now

_TERMINAL = {"succeeded", "failed", "cancelled"}


class SqlAlchemyJobQueue:
    """PostgreSQL queue with SKIP LOCKED and a SQLite development adapter."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def submit(
        self,
        job_type: str,
        payload: JobPayload,
        *,
        owner_id: int,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> Job:
        normalized_type = str(job_type).strip()
        normalized_owner = int(owner_id)
        normalized_key = str(idempotency_key).strip() if idempotency_key else None
        if not normalized_type or normalized_owner <= 0 or max_attempts <= 0:
            raise ValueError("invalid background job")
        now = utc_now()
        values = {
            "id": str(uuid.uuid4()),
            "job_type": normalized_type,
            "owner_id": normalized_owner,
            "status": "queued",
            "payload_json": encode_payload(payload),
            "idempotency_key": normalized_key,
            "attempts": 0,
            "max_attempts": int(max_attempts),
            "available_at": now,
            "cancel_requested": False,
            "created_at": now,
            "updated_at": now,
        }
        session = self._session_factory()
        try:
            with session.begin():
                row = session.execute(
                    insert(background_jobs).values(**values).returning(background_jobs)
                ).mappings().one()
            return to_job(row)
        except IntegrityError:
            session.rollback()
            if not normalized_key:
                raise
            existing = session.execute(
                select(background_jobs).where(
                    background_jobs.c.owner_id == normalized_owner,
                    background_jobs.c.job_type == normalized_type,
                    background_jobs.c.idempotency_key == normalized_key,
                )
            ).mappings().one()
            return to_job(existing)
        finally:
            session.close()

    def get(self, job_id: str, *, owner_id: int) -> Job | None:
        with self._session_factory() as session:
            row = session.execute(
                select(background_jobs).where(
                    background_jobs.c.id == str(job_id),
                    background_jobs.c.owner_id == int(owner_id),
                )
            ).mappings().first()
        return to_job(row) if row else None

    def lease(self, worker_id: str, *, lease_seconds: int) -> Job | None:
        now = utc_now()
        session = self._session_factory()
        try:
            with session.begin():
                self._recover_stale(session, now)
                statement = (
                    select(background_jobs)
                    .where(
                        background_jobs.c.status == "queued",
                        background_jobs.c.available_at <= now,
                    )
                    .order_by(
                        background_jobs.c.available_at,
                        background_jobs.c.created_at,
                    )
                    .limit(1)
                )
                if session.bind and session.bind.dialect.name == "postgresql":
                    statement = statement.with_for_update(skip_locked=True)
                candidate = session.execute(statement).mappings().first()
                if candidate is None:
                    return None
                row = session.execute(
                    update(background_jobs)
                    .where(
                        background_jobs.c.id == candidate["id"],
                        background_jobs.c.status == "queued",
                    )
                    .values(
                        status="running",
                        attempts=background_jobs.c.attempts + 1,
                        lease_owner=str(worker_id),
                        lease_expires_at=now + timedelta(seconds=lease_seconds),
                        heartbeat_at=now,
                        updated_at=now,
                    )
                    .returning(background_jobs)
                ).mappings().first()
                return to_job(row) if row else None
        finally:
            session.close()

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_seconds: int,
    ) -> bool:
        now = utc_now()
        with self._session_factory.begin() as session:
            result = session.execute(
                update(background_jobs)
                .where(
                    background_jobs.c.id == str(job_id),
                    background_jobs.c.status == "running",
                    background_jobs.c.lease_owner == str(worker_id),
                    background_jobs.c.cancel_requested.is_(False),
                )
                .values(
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    updated_at=now,
                )
            )
            return result.rowcount == 1

    def succeed(self, job_id: str, worker_id: str, result: JobPayload) -> bool:
        now = utc_now()
        with self._session_factory.begin() as session:
            statement = (
                update(background_jobs)
                .where(
                    background_jobs.c.id == str(job_id),
                    background_jobs.c.status == "running",
                    background_jobs.c.lease_owner == str(worker_id),
                    background_jobs.c.cancel_requested.is_(False),
                )
                .values(
                    status="succeeded",
                    result_json=encode_payload(result),
                    error=None,
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                    completed_at=now,
                    updated_at=now,
                )
            )
            return session.execute(statement).rowcount == 1

    def fail(
        self,
        job_id: str,
        worker_id: str,
        error: str,
        *,
        retry_delay_seconds: int,
    ) -> bool:
        now = utc_now()
        session = self._session_factory()
        try:
            with session.begin():
                row = session.execute(
                    select(background_jobs)
                    .where(
                        background_jobs.c.id == str(job_id),
                        background_jobs.c.status == "running",
                        background_jobs.c.lease_owner == str(worker_id),
                    )
                    .with_for_update()
                ).mappings().first()
                if row is None:
                    return False
                should_retry = (
                    not row["cancel_requested"]
                    and int(row["attempts"]) < int(row["max_attempts"])
                )
                status = "queued" if should_retry else (
                    "cancelled" if row["cancel_requested"] else "failed"
                )
                session.execute(
                    update(background_jobs)
                    .where(background_jobs.c.id == str(job_id))
                    .values(
                        status=status,
                        error=str(error)[:4000],
                        available_at=now + timedelta(seconds=retry_delay_seconds),
                        lease_owner=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                        completed_at=None if should_retry else now,
                        updated_at=now,
                    )
                )
                return True
        finally:
            session.close()

    def cancel(self, job_id: str, *, owner_id: int) -> Job | None:
        now = utc_now()
        session = self._session_factory()
        try:
            with session.begin():
                existing = session.execute(
                    select(background_jobs).where(
                        background_jobs.c.id == str(job_id),
                        background_jobs.c.owner_id == int(owner_id),
                    )
                ).mappings().first()
                if existing is None:
                    return None
                if existing["status"] in _TERMINAL:
                    return to_job(existing)
                row = session.execute(
                    update(background_jobs)
                    .where(
                        background_jobs.c.id == str(job_id),
                        background_jobs.c.owner_id == int(owner_id),
                    )
                    .values(
                        status="cancelled",
                        cancel_requested=True,
                        lease_owner=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                        completed_at=now,
                        updated_at=now,
                    )
                    .returning(background_jobs)
                ).mappings().one()
                return to_job(row)
        finally:
            session.close()

    def recover_stale(self) -> int:
        with self._session_factory.begin() as session:
            return self._recover_stale(session, utc_now())

    @staticmethod
    def _recover_stale(session: Session, now: datetime) -> int:
        retryable = session.execute(
            update(background_jobs)
            .where(
                background_jobs.c.status == "running",
                background_jobs.c.lease_expires_at.is_not(None),
                background_jobs.c.lease_expires_at <= now,
                background_jobs.c.attempts < background_jobs.c.max_attempts,
            )
            .values(
                status="queued",
                lease_owner=None,
                lease_expires_at=None,
                heartbeat_at=None,
                available_at=now,
                updated_at=now,
                error="worker lease expired; job recovered",
            )
        )
        exhausted = session.execute(
            update(background_jobs)
            .where(
                background_jobs.c.status == "running",
                background_jobs.c.lease_expires_at.is_not(None),
                background_jobs.c.lease_expires_at <= now,
                background_jobs.c.attempts >= background_jobs.c.max_attempts,
            )
            .values(
                status="failed",
                lease_owner=None,
                lease_expires_at=None,
                heartbeat_at=None,
                completed_at=now,
                updated_at=now,
                error="worker lease expired after final attempt",
            )
        )
        cancelled = session.execute(
            update(background_jobs)
            .where(
                background_jobs.c.status == "queued",
                background_jobs.c.cancel_requested.is_(True),
            )
            .values(status="cancelled", completed_at=now, updated_at=now)
        )
        return int(retryable.rowcount + exhausted.rowcount + cancelled.rowcount)

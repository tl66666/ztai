from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

JobPayload = dict[str, Any]


@dataclass(frozen=True)
class Job:
    id: str
    job_type: str
    owner_id: int
    status: str
    payload: JobPayload
    result: JobPayload | None
    error: str | None
    attempts: int
    max_attempts: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class JobQueue(Protocol):
    """Durable queue interface shared by API producers and worker consumers."""

    def submit(
        self,
        job_type: str,
        payload: JobPayload,
        *,
        owner_id: int,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> Job: ...

    def get(self, job_id: str, *, owner_id: int) -> Job | None: ...

    def lease(self, worker_id: str, *, lease_seconds: int) -> Job | None: ...

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_seconds: int,
    ) -> bool: ...

    def succeed(self, job_id: str, worker_id: str, result: JobPayload) -> bool: ...

    def fail(
        self,
        job_id: str,
        worker_id: str,
        error: str,
        *,
        retry_delay_seconds: int,
    ) -> bool: ...

    def cancel(self, job_id: str, *, owner_id: int) -> Job | None: ...

    def recover_stale(self) -> int: ...

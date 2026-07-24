from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.ports.job_queue import Job, JobPayload


def encode_payload(value: JobPayload) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def to_job(row: Any) -> Job:
    return Job(
        id=str(row["id"]),
        job_type=str(row["job_type"]),
        owner_id=int(row["owner_id"]),
        status=str(row["status"]),
        payload=_decode(row["payload_json"]) or {},
        result=_decode(row["result_json"]),
        error=row["error"],
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        cancel_requested=bool(row["cancel_requested"]),
        created_at=_aware(row["created_at"]),
        updated_at=_aware(row["updated_at"]),
        completed_at=_aware(row["completed_at"]) if row["completed_at"] else None,
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def _decode(value: str | None) -> JobPayload | None:
    return json.loads(value) if value is not None else None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)

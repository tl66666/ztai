from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)

from backend.adapters.persistence.sqlalchemy.base import metadata

background_jobs = Table(
    "background_jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("job_type", String(100), nullable=False),
    Column("owner_id", Integer, nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'queued'")),
    Column("payload_json", Text, nullable=False),
    Column("result_json", Text),
    Column("error", Text),
    Column("idempotency_key", String(200)),
    Column("attempts", Integer, nullable=False, server_default=text("0")),
    Column("max_attempts", Integer, nullable=False, server_default=text("3")),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("lease_owner", String(200)),
    Column("lease_expires_at", DateTime(timezone=True)),
    Column("heartbeat_at", DateTime(timezone=True)),
    Column(
        "cancel_requested",
        Boolean,
        nullable=False,
        server_default=text("false"),
    ),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
    UniqueConstraint(
        "owner_id",
        "job_type",
        "idempotency_key",
        name="uq_background_jobs_owner_type_idempotency",
    ),
)

Index(
    "idx_background_jobs_lease",
    background_jobs.c.status,
    background_jobs.c.available_at,
    background_jobs.c.created_at,
)
Index(
    "idx_background_jobs_owner_created",
    background_jobs.c.owner_id,
    background_jobs.c.created_at,
)

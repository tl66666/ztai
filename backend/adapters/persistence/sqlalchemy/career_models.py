from sqlalchemy import Column, ForeignKey, Index, Integer, Table, Text, text

from .base import metadata

career_profiles = Table(
    "career_profiles",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("headline", Text),
    Column("summary", Text),
    Column("target_roles_json", Text),
    Column("skills_json", Text),
    Column("preferences_json", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

action_items = Table(
    "action_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("application_id", ForeignKey("job_applications.id")),
    Column("title", Text, nullable=False),
    Column("action_type", Text),
    Column("description", Text),
    Column("completion_evidence", Text),
    Column("status", Text, server_default=text("'pending'")),
    Column("priority", Integer, server_default=text("0")),
    Column("due_at", Text),
    Column("completed_at", Text),
    Column("source", Text, server_default=text("'user'")),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

domain_events = Table(
    "domain_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("aggregate_type", Text, nullable=False),
    Column("aggregate_id", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("payload_json", Text),
    Column("source", Text),
    Column("occurred_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

career_reports = Table(
    "career_reports",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("report_type", Text, nullable=False),
    Column("title", Text),
    Column("period_start", Text),
    Column("period_end", Text),
    Column("content_json", Text, nullable=False),
    Column("status", Text, server_default=text("'ready'")),
    Column("generated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

agent_action_proposals = Table(
    "agent_action_proposals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("agent_run_id", Text),
    Column("action_type", Text, nullable=False),
    Column("target_type", Text),
    Column("target_id", Text),
    Column("payload_json", Text, nullable=False),
    Column("arguments_json", Text),
    Column("preview", Text),
    Column("rationale", Text),
    Column("status", Text, server_default=text("'pending'")),
    Column("risk_level", Text, server_default=text("'low'")),
    Column("expires_at", Text),
    Column("idempotency_key", Text),
    Column("result_json", Text),
    Column("error_code", Text),
    Column("reviewed_by", Text),
    Column("reviewed_at", Text),
    Column("executing_at", Text),
    Column("executed_at", Text),
    Column("completed_at", Text),
    Column("cancelled_at", Text),
    Column("failed_at", Text),
    Column("expired_at", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

Index("idx_career_profiles_user", career_profiles.c.user_id, unique=True)
Index(
    "idx_action_items_user_status_due",
    action_items.c.user_id,
    action_items.c.status,
    action_items.c.due_at,
)
Index("idx_action_items_application", action_items.c.application_id)
Index(
    "idx_domain_events_aggregate",
    domain_events.c.aggregate_type,
    domain_events.c.aggregate_id,
    domain_events.c.occurred_at,
)
Index("idx_domain_events_user", domain_events.c.user_id, domain_events.c.occurred_at)
Index(
    "idx_domain_events_agent_source_receipt",
    domain_events.c.user_id,
    domain_events.c.source,
    unique=True,
    sqlite_where=domain_events.c.source.like("agent:%"),
    postgresql_where=domain_events.c.source.like("agent:%"),
)
Index(
    "idx_career_reports_user_type",
    career_reports.c.user_id,
    career_reports.c.report_type,
    career_reports.c.generated_at,
)
Index(
    "idx_agent_proposals_user_status",
    agent_action_proposals.c.user_id,
    agent_action_proposals.c.status,
    agent_action_proposals.c.created_at,
)
Index(
    "idx_agent_proposals_user_status_expires",
    agent_action_proposals.c.user_id,
    agent_action_proposals.c.status,
    agent_action_proposals.c.expires_at,
    agent_action_proposals.c.created_at,
)
Index(
    "idx_agent_proposals_user_idempotency",
    agent_action_proposals.c.user_id,
    agent_action_proposals.c.idempotency_key,
    unique=True,
    sqlite_where=agent_action_proposals.c.idempotency_key.is_not(None),
    postgresql_where=agent_action_proposals.c.idempotency_key.is_not(None),
)

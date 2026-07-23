from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select

from .agent_session import AgentSessionProvider
from .career_models import action_items, domain_events
from .core_models import job_applications, job_matches, resumes
from .training_models import interviews, practice_records


class SqlAlchemyAgentContextStore:
    """Read-model adapter for the bounded career snapshot used by the agent."""

    def __init__(self, sessions: AgentSessionProvider):
        self.sessions = sessions

    def context_entity_owned(
        self,
        table_name: str,
        entity_id: int,
        user_id: int,
    ) -> bool:
        table = resumes if table_name == "resumes" else job_applications
        conditions = [table.c.id == entity_id, table.c.user_id == user_id]
        if table is job_applications:
            conditions.append(job_applications.c.deleted_at.is_(None))
        with self.sessions.session() as session:
            return session.execute(select(table.c.id).where(*conditions)).first() is not None

    def counts(self, user_id: int) -> dict[str, int]:
        tables = {
            "简历": resumes,
            "投递": job_applications,
            "面试训练": interviews,
        }
        counts: dict[str, int] = {}
        with self.sessions.session() as session:
            for label, table in tables.items():
                statement = (
                    select(func.count()).select_from(table).where(table.c.user_id == user_id)
                )
                if table is job_applications:
                    statement = statement.where(job_applications.c.deleted_at.is_(None))
                counts[label] = int(session.execute(statement).scalar_one())
        return counts

    def opportunities(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        job_applications.c.id,
                        job_applications.c.company,
                        job_applications.c.job_title,
                        job_applications.c.status,
                        job_applications.c.city,
                        job_applications.c.priority,
                        job_applications.c.resume_id,
                        job_applications.c.next_action_at,
                        job_applications.c.interview_at,
                        job_applications.c.deadline_at,
                        job_applications.c.updated_at,
                    )
                    .where(
                        job_applications.c.user_id == user_id,
                        job_applications.c.deleted_at.is_(None),
                    )
                    .order_by(
                        job_applications.c.priority.desc(),
                        job_applications.c.updated_at.desc(),
                        job_applications.c.id.desc(),
                    )
                    .limit(100)
                ).mappings()
            )

    def selected_opportunity(
        self,
        opportunity_id: int,
        user_id: int,
    ) -> Mapping[str, Any] | None:
        columns = (
            job_applications.c.id,
            job_applications.c.company,
            job_applications.c.job_title,
            job_applications.c.status,
            job_applications.c.city,
            job_applications.c.salary_min,
            job_applications.c.salary_max,
            job_applications.c.priority,
            job_applications.c.resume_id,
            job_applications.c.source_url,
            job_applications.c.channel,
            job_applications.c.next_action_at,
            job_applications.c.interview_at,
            job_applications.c.deadline_at,
            job_applications.c.applied_at,
            job_applications.c.created_at,
            job_applications.c.updated_at,
        )
        with self.sessions.session() as session:
            return (
                session.execute(
                    select(*columns).where(
                        job_applications.c.id == opportunity_id,
                        job_applications.c.user_id == user_id,
                        job_applications.c.deleted_at.is_(None),
                    )
                )
                .mappings()
                .first()
            )

    def resumes(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        resumes.c.id,
                        resumes.c.title,
                        resumes.c.version_label,
                        resumes.c.target_job_title,
                        resumes.c.status,
                        resumes.c.updated_at,
                    )
                    .where(
                        resumes.c.user_id == user_id,
                        func.coalesce(resumes.c.status, "active") != "archived",
                    )
                    .order_by(resumes.c.id.desc())
                    .limit(100)
                ).mappings()
            )

    def action_items(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        action_items.c.id,
                        action_items.c.application_id,
                        action_items.c.title,
                        action_items.c.action_type.label("type"),
                        action_items.c.status,
                        action_items.c.priority,
                        action_items.c.due_at,
                        action_items.c.completed_at,
                        action_items.c.completion_evidence,
                        action_items.c.source,
                    )
                    .where(
                        action_items.c.user_id == user_id,
                        action_items.c.status.in_(("pending", "in_progress")),
                    )
                    .order_by(
                        action_items.c.updated_at.desc(),
                        action_items.c.id.desc(),
                    )
                    .limit(8)
                ).mappings()
            )

    def recent_events(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        domain_events.c.aggregate_type,
                        domain_events.c.aggregate_id,
                        domain_events.c.event_type,
                        domain_events.c.payload_json,
                        domain_events.c.occurred_at,
                    )
                    .where(domain_events.c.user_id == user_id)
                    .order_by(
                        domain_events.c.occurred_at.desc(),
                        domain_events.c.id.desc(),
                    )
                    .limit(12)
                ).mappings()
            )

    def score_trends(self, user_id: int) -> dict[str, list]:
        sources = {
            "matches": (job_matches, job_matches.c.match_score),
            "interviews": (interviews, interviews.c.score),
            "practice": (practice_records, practice_records.c.score),
        }
        trends: dict[str, list] = {}
        with self.sessions.session() as session:
            for label, (table, score) in sources.items():
                rows = list(
                    session.execute(
                        select(score)
                        .where(table.c.user_id == user_id, score.is_not(None))
                        .order_by(table.c.created_at.desc(), table.c.id.desc())
                        .limit(5)
                    ).scalars()
                )
                trends[label] = [
                    value for value in reversed(rows) if isinstance(value, (int, float))
                ]
        return trends

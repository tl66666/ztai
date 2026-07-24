from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import insert, select, update

from .agent_session import AgentSessionProvider
from .career_models import (
    action_items,
    agent_action_proposals,
    career_profiles,
    career_reports,
    domain_events,
)
from .core_models import job_applications, resumes

OWNED_TABLES = {
    "career_profiles": career_profiles,
    "job_applications": job_applications,
    "resumes": resumes,
    "action_items": action_items,
    "career_reports": career_reports,
}


class SqlAlchemyAgentActionStore:
    """Transactional adapter for proposal lifecycle and validation reads."""

    def __init__(self, sessions: AgentSessionProvider):
        self.sessions = sessions

    def insert_proposal(self, values: Mapping[str, Any]) -> int:
        with self.sessions.session() as session:
            return int(
                session.execute(
                    insert(agent_action_proposals)
                    .values(**values)
                    .returning(agent_action_proposals.c.id)
                ).scalar_one()
            )

    def proposal(
        self,
        proposal_id: int,
        user_id: int,
    ) -> tuple[Mapping[str, Any] | None, bool]:
        with self.sessions.session() as session:
            row = (
                session.execute(
                    select(agent_action_proposals).where(
                        agent_action_proposals.c.id == proposal_id,
                        agent_action_proposals.c.user_id == user_id,
                    )
                )
                .mappings()
                .first()
            )
            if row is not None:
                return row, True
            exists = session.execute(
                select(agent_action_proposals.c.id).where(
                    agent_action_proposals.c.id == proposal_id
                )
            ).first()
            return None, exists is None

    def edit_proposal(
        self,
        proposal_id: int,
        user_id: int,
        values: Mapping[str, Any],
    ) -> bool:
        with self.sessions.session() as session:
            result = session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id == proposal_id,
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status == "pending",
                )
                .values(**values)
            )
            return result.rowcount == 1

    def cancel_proposal(self, proposal_id: int, user_id: int, now: str) -> bool:
        return self.edit_proposal(
            proposal_id,
            user_id,
            {
                "status": "cancelled",
                "cancelled_at": now,
                "reviewed_by": "local_user",
                "reviewed_at": now,
                "updated_at": now,
            },
        )

    def list_proposals(
        self,
        user_id: int,
        status: str | None,
    ) -> list[Mapping[str, Any]]:
        statement = select(agent_action_proposals).where(
            agent_action_proposals.c.user_id == user_id
        )
        if status is not None:
            statement = statement.where(agent_action_proposals.c.status == status)
        statement = statement.order_by(
            agent_action_proposals.c.created_at,
            agent_action_proposals.c.id,
        )
        with self.sessions.session() as session:
            return list(session.execute(statement).mappings())

    def pending_expiries(
        self,
        user_id: int,
        proposal_id: int | None = None,
    ) -> list[Mapping[str, Any]]:
        statement = select(
            agent_action_proposals.c.id,
            agent_action_proposals.c.expires_at,
        ).where(
            agent_action_proposals.c.user_id == user_id,
            agent_action_proposals.c.status == "pending",
        )
        if proposal_id is not None:
            statement = statement.where(agent_action_proposals.c.id == proposal_id)
        with self.sessions.session() as session:
            return list(session.execute(statement).mappings())

    def expire(self, user_id: int, proposal_ids: Sequence[int], now: str) -> None:
        if not proposal_ids:
            return
        with self.sessions.session() as session:
            session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id.in_(proposal_ids),
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status == "pending",
                )
                .values(status="expired", expired_at=now, updated_at=now)
            )

    def claim_pending(
        self,
        proposal_id: int,
        user_id: int,
        now: str,
    ) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            statement = select(agent_action_proposals).where(
                agent_action_proposals.c.id == proposal_id,
                agent_action_proposals.c.user_id == user_id,
            )
            if self.sessions.dialect_name == "postgresql":
                statement = statement.with_for_update()
            row = session.execute(statement).mappings().first()
            if row is None or row["status"] != "pending":
                return None
            result = session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id == proposal_id,
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status == "pending",
                )
                .values(
                    status="executing",
                    reviewed_by="local_user",
                    reviewed_at=now,
                    executing_at=now,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            return {
                **row,
                "status": "executing",
                "reviewed_by": "local_user",
                "reviewed_at": now,
                "executing_at": now,
            }

    def claim_stale(
        self,
        proposal_id: int,
        user_id: int,
        previous_executing_at: str | None,
        now: str,
    ) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            statement = select(agent_action_proposals).where(
                agent_action_proposals.c.id == proposal_id,
                agent_action_proposals.c.user_id == user_id,
            )
            if self.sessions.dialect_name == "postgresql":
                statement = statement.with_for_update()
            row = session.execute(statement).mappings().first()
            if (
                row is None
                or row["status"] != "executing"
                or row["executing_at"] != previous_executing_at
            ):
                return None
            previous_condition = (
                agent_action_proposals.c.executing_at.is_(None)
                if previous_executing_at is None
                else agent_action_proposals.c.executing_at == previous_executing_at
            )
            result = session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id == proposal_id,
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status == "executing",
                    previous_condition,
                )
                .values(executing_at=now, updated_at=now)
            )
            if result.rowcount != 1:
                return None
            return {**row, "executing_at": now}

    def receipt_payload(self, user_id: int, source: str) -> str | None:
        with self.sessions.session() as session:
            return session.execute(
                select(domain_events.c.payload_json).where(
                    domain_events.c.user_id == user_id,
                    domain_events.c.source == source,
                )
            ).scalar_one_or_none()

    def owned(self, table_name: str, row_id: int, user_id: int, active_only: bool) -> bool:
        table = OWNED_TABLES[table_name]
        conditions = [table.c.id == row_id, table.c.user_id == user_id]
        if active_only:
            conditions.append(table.c.deleted_at.is_(None))
        with self.sessions.session() as session:
            return session.execute(select(table.c.id).where(*conditions)).first() is not None

    def action_item(self, action_id: int, user_id: int) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            return (
                session.execute(
                    select(
                        action_items.c.action_type,
                        action_items.c.status,
                        action_items.c.application_id,
                    ).where(
                        action_items.c.id == action_id,
                        action_items.c.user_id == user_id,
                    )
                )
                .mappings()
                .first()
            )

    def opportunity_status(self, opportunity_id: int, user_id: int) -> str | None:
        with self.sessions.session() as session:
            return session.execute(
                select(job_applications.c.status).where(
                    job_applications.c.id == opportunity_id,
                    job_applications.c.user_id == user_id,
                    job_applications.c.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

    def opportunity_salary(
        self,
        opportunity_id: int,
        user_id: int,
    ) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            return (
                session.execute(
                    select(
                        job_applications.c.salary_min,
                        job_applications.c.salary_max,
                    ).where(
                        job_applications.c.id == opportunity_id,
                        job_applications.c.user_id == user_id,
                        job_applications.c.deleted_at.is_(None),
                    )
                )
                .mappings()
                .first()
            )

    def finalize_completed(
        self,
        proposal_id: int,
        user_id: int,
        result_json: str,
        now: str,
    ) -> None:
        with self.sessions.session() as session:
            row = (
                session.execute(
                    select(
                        agent_action_proposals.c.executed_at,
                        agent_action_proposals.c.completed_at,
                    ).where(
                        agent_action_proposals.c.id == proposal_id,
                        agent_action_proposals.c.user_id == user_id,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return
            session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id == proposal_id,
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status.in_(("executing", "completed")),
                )
                .values(
                    status="completed",
                    result_json=result_json,
                    error_code=None,
                    executed_at=row["executed_at"] or now,
                    completed_at=row["completed_at"] or now,
                    updated_at=now,
                )
            )

    def mark_failed(self, proposal_id: int, user_id: int, now: str) -> None:
        with self.sessions.session() as session:
            session.execute(
                update(agent_action_proposals)
                .where(
                    agent_action_proposals.c.id == proposal_id,
                    agent_action_proposals.c.user_id == user_id,
                    agent_action_proposals.c.status == "executing",
                )
                .values(
                    status="failed",
                    error_code="execution_failed",
                    failed_at=now,
                    updated_at=now,
                )
            )

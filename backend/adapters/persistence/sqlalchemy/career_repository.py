from __future__ import annotations

from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from .career_models import action_items, career_profiles, career_reports, domain_events
from .core_models import job_applications, job_matches, resumes
from .event_repository import SqlAlchemyEventRepository
from .training_models import audio_records, interviews, practice_records


class SqlAlchemyCareerRepository:
    """All Career aggregate persistence behind one transactional adapter."""

    _OWNED_TABLES = {
        "resumes": resumes,
        "job_applications": job_applications,
        "action_items": action_items,
        "career_reports": career_reports,
    }

    def __init__(
        self,
        session: Session,
        events: SqlAlchemyEventRepository | None = None,
    ):
        self.session = session
        self.events = events or SqlAlchemyEventRepository(session)

    def profile(self, user_id: int) -> dict[str, Any] | None:
        return self._first(select(career_profiles).where(career_profiles.c.user_id == user_id))

    def dashboard_counts(self, user_id: int) -> dict[str, int]:
        return {
            "resumes": self._count(resumes, user_id),
            "matches": self._count(job_matches, user_id),
            "interviews": self._count(interviews, user_id),
            "applications": int(
                self.session.execute(
                    select(func.count())
                    .select_from(job_applications)
                    .where(
                        job_applications.c.user_id == user_id,
                        job_applications.c.deleted_at.is_(None),
                    )
                ).scalar_one()
            ),
        }

    def readiness_evidence(self, user_id: int) -> dict[str, Any]:
        resume = self._first(
            select(resumes)
            .where(
                resumes.c.user_id == user_id,
                (resumes.c.status.is_(None)) | (resumes.c.status.in_(("active", "main"))),
            )
            .order_by(resumes.c.updated_at.desc(), resumes.c.id.desc())
            .limit(1)
        )
        match_rows = self._all(
            select(
                job_matches.c.id,
                job_matches.c.resume_id,
                job_matches.c.job_title,
                job_matches.c.application_id,
                job_matches.c.match_score,
                job_matches.c.analysis,
                func.coalesce(job_matches.c.jd_text, job_applications.c.jd_text).label(
                    "jd_text"
                ),
                job_matches.c.created_at,
            )
            .join(
                resumes,
                (resumes.c.id == job_matches.c.resume_id)
                & (resumes.c.user_id == job_matches.c.user_id),
            )
            .outerjoin(
                job_applications,
                (job_applications.c.id == job_matches.c.application_id)
                & (job_applications.c.user_id == job_matches.c.user_id)
                & (job_applications.c.deleted_at.is_(None)),
            )
            .where(
                job_matches.c.user_id == user_id,
                (job_matches.c.application_id.is_(None))
                | (job_applications.c.id.is_not(None)),
            )
            .order_by(job_matches.c.created_at.desc(), job_matches.c.id.desc())
        )
        return {
            "resume": resume,
            "matches": match_rows,
            "interviews": self._readiness_rows(interviews, user_id),
            "practices": self._readiness_rows(practice_records, user_id),
            "audios": self._readiness_rows(audio_records, user_id),
            "opportunities": self._all(
                select(
                    job_applications.c.id,
                    job_applications.c.status,
                    job_applications.c.next_action_at,
                    job_applications.c.updated_at,
                )
                .where(
                    job_applications.c.user_id == user_id,
                    job_applications.c.deleted_at.is_(None),
                )
                .order_by(job_applications.c.id.desc())
                .limit(50)
            ),
        }

    def upsert_profile(
        self,
        user_id: int,
        *,
        headline: str | None,
        summary: str | None,
        target_roles_json: str,
        skills_json: str,
        preferences_json: str,
    ) -> dict[str, Any]:
        existing = self.profile(user_id)
        values = {
            "headline": headline,
            "summary": summary,
            "target_roles_json": target_roles_json,
            "skills_json": skills_json,
            "preferences_json": preferences_json,
            "updated_at": func.current_timestamp(),
        }
        if existing:
            self.session.execute(
                update(career_profiles)
                .where(career_profiles.c.user_id == user_id)
                .values(**values)
            )
        else:
            self.session.execute(insert(career_profiles).values(user_id=user_id, **values))
        return self.profile(user_id) or {}

    def list_opportunities(self, user_id: int) -> list[dict[str, Any]]:
        return self._all(
            select(job_applications)
            .where(
                job_applications.c.user_id == user_id,
                job_applications.c.deleted_at.is_(None),
            )
            .order_by(job_applications.c.updated_at.desc(), job_applications.c.id.desc())
        )

    def owned(
        self,
        table_name: str,
        row_id: int,
        user_id: int,
        *,
        include_deleted: bool = False,
    ) -> dict[str, Any] | None:
        table = self._OWNED_TABLES[table_name]
        conditions = [table.c.id == row_id, table.c.user_id == user_id]
        if table is job_applications and not include_deleted:
            conditions.append(job_applications.c.deleted_at.is_(None))
        return self._first(select(table).where(*conditions))

    def add_opportunity(self, user_id: int, values: dict[str, Any]) -> int:
        persisted = {key: value for key, value in values.items() if key != "user_id"}
        result = self.session.execute(
            insert(job_applications).values(user_id=user_id, **persisted)
        )
        return int(result.inserted_primary_key[0])

    def update_opportunity(
        self, opportunity_id: int, user_id: int, changes: dict[str, Any]
    ) -> None:
        self.session.execute(
            update(job_applications)
            .where(
                job_applications.c.id == opportunity_id,
                job_applications.c.user_id == user_id,
            )
            .values(**changes, updated_at=func.current_timestamp())
        )

    def soft_delete_opportunity(self, opportunity_id: int, user_id: int) -> None:
        self.session.execute(
            update(job_applications)
            .where(
                job_applications.c.id == opportunity_id,
                job_applications.c.user_id == user_id,
                job_applications.c.deleted_at.is_(None),
            )
            .values(
                deleted_at=func.current_timestamp(),
                updated_at=func.current_timestamp(),
            )
        )

    def add_resume_version(self, user_id: int, values: dict[str, Any]) -> int:
        result = self.session.execute(insert(resumes).values(user_id=user_id, **values))
        return int(result.inserted_primary_key[0])

    def add_action(self, user_id: int, values: dict[str, Any]) -> int:
        result = self.session.execute(insert(action_items).values(user_id=user_id, **values))
        return int(result.inserted_primary_key[0])

    def list_actions(self, user_id: int) -> list[dict[str, Any]]:
        return self._all(
            select(action_items)
            .where(action_items.c.user_id == user_id)
            .order_by(action_items.c.due_at, action_items.c.id.desc())
        )

    def complete_action(self, action_id: int, user_id: int, evidence: str) -> None:
        self.session.execute(
            update(action_items)
            .where(action_items.c.id == action_id, action_items.c.user_id == user_id)
            .values(
                status="completed",
                completed_at=func.current_timestamp(),
                completion_evidence=evidence,
                updated_at=func.current_timestamp(),
            )
        )

    def add_report(self, user_id: int, values: dict[str, Any]) -> int:
        result = self.session.execute(insert(career_reports).values(user_id=user_id, **values))
        return int(result.inserted_primary_key[0])

    def timeline(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        return self._all(
            select(domain_events)
            .where(
                domain_events.c.user_id == user_id,
                domain_events.c.aggregate_type == "opportunity",
                domain_events.c.aggregate_id == str(opportunity_id),
            )
            .order_by(domain_events.c.occurred_at, domain_events.c.id)
        )

    def add_event(
        self,
        user_id: int,
        aggregate_type: str,
        aggregate_id: int | str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.events.record_and_apply(
            user_id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload,
        )

    def _readiness_rows(self, table, user_id: int) -> list[dict[str, Any]]:
        return self._all(
            select(table)
            .where(table.c.user_id == user_id)
            .order_by(table.c.created_at.desc(), table.c.id.desc())
        )

    def _count(self, table, user_id: int) -> int:
        return int(
            self.session.execute(
                select(func.count()).select_from(table).where(table.c.user_id == user_id)
            ).scalar_one()
        )

    def _first(self, statement) -> dict[str, Any] | None:
        row = self.session.execute(statement).mappings().first()
        return dict(row) if row is not None else None

    def _all(self, statement) -> list[dict[str, Any]]:
        return [dict(row) for row in self.session.execute(statement).mappings()]

from __future__ import annotations

import json
import os
from typing import Any

from utils.domain import APPLICATION_STATUSES, CareerService
from utils.domain.database import connect

_WORKSPACE_OPPORTUNITY_FIELDS = (
    "id",
    "company",
    "job_title",
    "status",
    "city",
    "salary_min",
    "salary_max",
    "notes",
    "applied_at",
    "next_action_at",
    "interview_at",
    "priority",
    "jd_text",
    "resume_id",
    "created_at",
    "updated_at",
    "needs_status_review",
)


class OpportunityModule:
    """Deep application module for opportunity commands and safe workspace reads."""

    def __init__(
        self,
        service: CareerService,
        db_path: str | os.PathLike[str],
        *,
        local_user_id: int,
    ):
        self._service = service
        self._db_path = os.fspath(db_path)
        self._local_user_id = int(local_user_id)

    def list(self) -> dict[str, Any]:
        return {
            "success": True,
            "data": self._service.list_opportunities(self._local_user_id),
            "canonical_statuses": APPLICATION_STATUSES,
        }

    def create(self, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        opportunity = self._service.create_opportunity(self._local_user_id, body)
        return {"success": True, "data": opportunity}, 201

    def get(self, opportunity_id: int) -> dict[str, Any]:
        opportunity = self._service.get_opportunity(
            self._local_user_id, opportunity_id
        )
        return {"success": True, "data": opportunity}

    def update(
        self, opportunity_id: int, body: dict[str, Any]
    ) -> dict[str, Any]:
        opportunity = self._service.update_opportunity(
            self._local_user_id, opportunity_id, body
        )
        return {"success": True, "data": opportunity}

    def timeline(self, opportunity_id: int) -> dict[str, Any]:
        events = self._service.timeline(self._local_user_id, opportunity_id)
        return {"success": True, "data": events}

    def workspace(self, opportunity_id: int) -> dict[str, Any]:
        opportunity = self._service.get_opportunity(
            self._local_user_id, opportunity_id
        )
        timeline = self._service.timeline(self._local_user_id, opportunity_id)
        safe_opportunity = {
            field: opportunity.get(field)
            for field in _WORKSPACE_OPPORTUNITY_FIELDS
            if field in opportunity
        }

        with connect(self._db_path) as connection:
            resume = self._resume(connection, opportunity)
            matches = self._matches(connection, opportunity_id)
            interviews = self._interviews(connection, opportunity_id)
            actions = self._actions(connection, opportunity_id)

        safe_timeline = [
            {
                "id": event["id"],
                "event_type": event["event_type"],
                "source": event.get("source"),
                "occurred_at": event["occurred_at"],
            }
            for event in timeline
        ]
        return {
            "success": True,
            "opportunity": safe_opportunity,
            "resume": resume,
            "matches": matches,
            "interviews": interviews,
            "actions": actions,
            "timeline": safe_timeline,
        }

    def _resume(self, connection, opportunity: dict[str, Any]):
        if opportunity.get("resume_id") is None:
            return None
        row = connection.execute(
            """
            SELECT id, title, file_path, file_type, status, version_label,
                   target_job_title, created_at, updated_at
            FROM resumes WHERE id = ? AND user_id = ?
            """,
            (opportunity["resume_id"], self._local_user_id),
        ).fetchone()
        if not row:
            return None
        resume = dict(row)
        resume["has_original"] = bool(resume.pop("file_path", None))
        return resume

    def _matches(self, connection, opportunity_id: int) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT m.id, m.resume_id, m.job_title, m.match_score, m.analysis,
                   m.details_json, m.created_at, r.title AS resume_title
            FROM job_matches m
            JOIN resumes r ON r.id = m.resume_id AND r.user_id = m.user_id
            WHERE m.user_id = ? AND m.application_id = ?
            ORDER BY m.created_at DESC, m.id DESC LIMIT 5
            """,
            (self._local_user_id, opportunity_id),
        ).fetchall()
        matches = []
        for row in rows:
            item = dict(row)
            raw_details = item.pop("details_json", None)
            try:
                details = json.loads(raw_details or "{}")
            except (TypeError, json.JSONDecodeError):
                details = {}
            item["details"] = details if isinstance(details, dict) else {}
            matches.append(item)
        return matches

    def _interviews(self, connection, opportunity_id: int) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, resume_id, job_title, mode, status, current_stage,
                       score, feedback, started_at, completed_at, updated_at
                FROM interview_sessions
                WHERE user_id = ? AND application_id = ?
                ORDER BY started_at DESC, id DESC
                """,
                (self._local_user_id, opportunity_id),
            ).fetchall()
        ]

    def _actions(self, connection, opportunity_id: int) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, title, action_type, description, status, priority,
                       due_at, completed_at, created_at, updated_at
                FROM action_items
                WHERE user_id = ? AND application_id = ?
                ORDER BY CASE status
                    WHEN 'pending' THEN 0
                    WHEN 'in_progress' THEN 1
                    ELSE 2
                END, due_at, id
                """,
                (self._local_user_id, opportunity_id),
            ).fetchall()
        ]

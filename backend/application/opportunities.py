from __future__ import annotations

import json
from typing import Any

from backend.ports.persistence import UnitOfWorkFactory
from utils.domain import APPLICATION_STATUSES, CareerService

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
        unit_of_work: UnitOfWorkFactory,
        *,
        local_user_id: int,
    ):
        self._service = service
        self._unit_of_work = unit_of_work
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

        with self._unit_of_work() as unit_of_work:
            snapshot = unit_of_work.opportunities.snapshot(
                self._local_user_id,
                opportunity_id=opportunity_id,
                resume_id=opportunity.get("resume_id"),
            )
        resume = snapshot["resume"]
        if resume is not None:
            resume["has_original"] = bool(resume.pop("file_path", None))
        matches = []
        for item in snapshot["matches"]:
            raw_details = item.pop("details_json", None)
            try:
                details = json.loads(raw_details or "{}")
            except (TypeError, json.JSONDecodeError):
                details = {}
            item["details"] = details if isinstance(details, dict) else {}
            matches.append(item)

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
            "interviews": snapshot["interviews"],
            "actions": snapshot["actions"],
            "timeline": safe_timeline,
        }

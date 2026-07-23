from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from backend.adapters.persistence.sqlalchemy.source import coerce_unit_of_work_factory

from .career_dto import CareerDtoMixin
from .career_readiness import (
    DELIVERABLE_THRESHOLD,
    JD_REQUIREMENT_MARKERS,
    JD_RESPONSIBILITY_MARKERS,
    MIN_JD_UNIQUE_CHARACTERS,
    MIN_MEANINGFUL_JD_LENGTH,
    POLISH_THRESHOLD,
    READINESS_RECENT_LIMIT,
    READINESS_WEIGHTS,
    CareerReadinessMixin,
    is_meaningful_jd_snapshot,
)
from .database import APPLICATION_STATUSES
from .events import apply_event_to_actions

DEFAULT_APPLICATION_STATUS = "已投递"
ACTION_STATUSES = ("pending", "in_progress", "completed", "cancelled")
RESUME_STATUSES = ("draft", "active", "archived")
RESUME_SOURCE_TYPES = ("upload", "manual", "agent")

_ACTIVE_PIPELINE = APPLICATION_STATUSES[:8]
ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {}
for index, status in enumerate(_ACTIVE_PIPELINE):
    allowed = set(_ACTIVE_PIPELINE[index:]) | {"Offer", "已拒绝", "已结束"}
    if index:
        allowed.add(_ACTIVE_PIPELINE[index - 1])
    ALLOWED_STATUS_TRANSITIONS[status] = frozenset(allowed)
ALLOWED_STATUS_TRANSITIONS.update(
    {
        "Offer": frozenset({"Offer", "已结束"}),
        "已拒绝": frozenset({"已拒绝", "已结束"}),
        "已结束": frozenset({"已结束"}),
    }
)


class CareerService(CareerReadinessMixin, CareerDtoMixin):
    def __init__(self, persistence, local_user_id: int = 1):
        self.db_path = os.fspath(persistence) if isinstance(persistence, (str, os.PathLike)) else ""
        self._unit_of_work = coerce_unit_of_work_factory(persistence)
        self.local_user_id = int(local_user_id)

    def get_profile(self, user_id: int) -> dict[str, Any] | None:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            row = unit_of_work.career.profile(self.local_user_id)
        return self._profile_from_row(row) if row else None

    def agent_dashboard_summary(self, user_id: int) -> dict[str, Any]:
        """Return compatibility counts plus canonical readiness, without row contents."""
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            counts = unit_of_work.career.dashboard_counts(self.local_user_id)
        return {**counts, "readiness": self.calculate_readiness(user_id)}

    def upsert_profile(
        self, user_id: int, values: dict[str, Any], source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        values = self._require_mapping(values, "profile values")
        source = self._bounded_text(source, "source", 100, required=True)
        with self._unit_of_work() as unit_of_work:
            existing = unit_of_work.career.profile(self.local_user_id)
            current = self._profile_from_row(existing) if existing else self._empty_profile()
            merged = self._merge_profile(current, values, source)
            serialized = self._serialize_profile(merged)
            row = unit_of_work.career.upsert_profile(
                self.local_user_id,
                headline=serialized[0],
                summary=serialized[1],
                target_roles_json=serialized[2],
                skills_json=serialized[3],
                preferences_json=serialized[4],
            )
            self._write_event(
                unit_of_work.career,
                "profile",
                self.local_user_id,
                "profile.updated",
                self._agent_receipt_payload(
                    {"fields": sorted(values)}, source, "career_profile", row["id"]
                ),
            )
        return self._profile_from_row(row)

    def list_opportunities(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            rows = unit_of_work.career.list_opportunities(self.local_user_id)
        return [self._opportunity_from_row(row) for row in rows]

    def get_opportunity(self, user_id: int, opportunity_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            row = unit_of_work.career.owned("job_applications", opportunity_id, self.local_user_id)
        if not row:
            raise LookupError("opportunity not found")
        return self._opportunity_from_row(row)

    def create_opportunity(
        self, user_id: int, values: dict[str, Any], source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        values = self._validate_opportunity_values(values, creating=True)
        source = self._bounded_text(source, "source", 100, required=True)
        values.setdefault("status", DEFAULT_APPLICATION_STATUS)
        values["created_by"] = source
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            if values.get("resume_id") is not None and not repository.owned(
                "resumes", values["resume_id"], self.local_user_id
            ):
                raise LookupError("resume not found")
            opportunity_id = repository.add_opportunity(self.local_user_id, values)
            self._write_event(
                repository,
                "opportunity",
                opportunity_id,
                "opportunity.created",
                self._agent_receipt_payload(
                    self._compact_opportunity_payload(values, source),
                    source,
                    "opportunity",
                    opportunity_id,
                    values["status"],
                ),
            )
            row = repository.owned("job_applications", opportunity_id, self.local_user_id)
        return self._opportunity_from_row(row)

    def update_opportunity(
        self,
        user_id: int,
        opportunity_id: int,
        changes: dict[str, Any],
        source: str = "user",
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        changes = self._validate_opportunity_values(changes, creating=False)
        source = self._bounded_text(source, "source", 100, required=True)
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            existing = repository.owned("job_applications", opportunity_id, self.local_user_id)
            if not existing:
                raise LookupError("opportunity not found")
            merged_salary_min = changes.get("salary_min", existing["salary_min"])
            merged_salary_max = changes.get("salary_max", existing["salary_max"])
            if merged_salary_min is not None and merged_salary_max is not None:
                if merged_salary_min > merged_salary_max:
                    raise ValueError("salary_min cannot exceed salary_max")
            if changes.get("resume_id") is not None and not repository.owned(
                "resumes", changes["resume_id"], self.local_user_id
            ):
                raise LookupError("resume not found")
            if "status" in changes:
                allowed = ALLOWED_STATUS_TRANSITIONS.get(
                    existing["status"], frozenset(APPLICATION_STATUSES)
                )
                if changes["status"] not in allowed:
                    raise ValueError("invalid status transition")
            changes = {field: value for field, value in changes.items() if existing[field] != value}
            if changes:
                repository.update_opportunity(
                    opportunity_id,
                    self.local_user_id,
                    changes,
                )
            result_status = changes.get("status", existing["status"])
            if changes or source.startswith("agent:"):
                self._write_event(
                    repository,
                    "opportunity",
                    opportunity_id,
                    "opportunity.updated",
                    self._agent_receipt_payload(
                        self._compact_opportunity_payload(changes, source),
                        source,
                        "opportunity",
                        opportunity_id,
                        result_status,
                    ),
                )
            row = repository.owned("job_applications", opportunity_id, self.local_user_id)
        return self._opportunity_from_row(row)

    def delete_opportunity(
        self, user_id: int, opportunity_id: int, source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        source = self._bounded_text(source, "source", 100, required=True)
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            existing = repository.owned("job_applications", opportunity_id, self.local_user_id)
            if not existing:
                raise LookupError("opportunity not found")
            self._write_event(
                repository,
                "opportunity",
                opportunity_id,
                "opportunity.deleted",
                {"source": source},
            )
            repository.soft_delete_opportunity(opportunity_id, self.local_user_id)
            row = repository.owned("job_applications", opportunity_id, self.local_user_id)
            if row is None:
                row = {
                    **existing,
                    "deleted_at": datetime.now(UTC).isoformat(),
                }
        return self._opportunity_from_row(row)

    def create_resume_version(
        self,
        user_id: int,
        resume_id: int,
        content: str,
        metadata: dict[str, Any],
        source: str = "user",
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        content = self._bounded_text(content, "content", 1_000_000, required=True)
        metadata = self._require_mapping(metadata, "metadata")
        permitted = {
            "version_label",
            "target_job_title",
            "application_id",
            "status",
            "source_type",
            "title",
            "action_id",
        }
        unknown = set(metadata) - permitted
        if unknown:
            raise ValueError(f"unknown resume metadata: {', '.join(sorted(unknown))}")
        for field in ("version_label", "target_job_title", "status", "source_type", "title"):
            if field in metadata:
                metadata[field] = self._bounded_text(metadata[field], field, 300)
        resume_status = self._bounded_text(
            metadata.get("status", "active"), "resume status", 20, required=True
        )
        if resume_status not in RESUME_STATUSES:
            raise ValueError("invalid resume status")
        source_type = self._bounded_text(
            metadata.get("source_type", "manual"), "source_type", 20, required=True
        )
        if source_type not in RESUME_SOURCE_TYPES:
            raise ValueError("invalid source_type")
        source = self._bounded_text(source, "source", 100, required=True)
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            source_row = repository.owned("resumes", resume_id, self.local_user_id)
            if not source_row:
                raise LookupError("resume not found")
            application_id = metadata.get("application_id")
            if application_id is not None and not repository.owned(
                "job_applications", application_id, self.local_user_id
            ):
                raise LookupError("opportunity not found")
            action_id = metadata.get("action_id")
            if action_id is not None:
                action_id = self._integer(action_id, "action_id")
                action = repository.owned("action_items", action_id, self.local_user_id)
                if not action:
                    raise LookupError("action item not found")
                if action["status"] not in {"pending", "in_progress"}:
                    raise ValueError("resume action item is not active")
                if action["action_type"] not in {"create_resume_version", "resume_version"}:
                    raise ValueError("action item is not a resume version action")
                if application_id is None or action["application_id"] != application_id:
                    raise ValueError("resume action item opportunity does not match")
            title = metadata.get("title") or metadata.get("version_label") or source_row["title"]
            new_id = repository.add_resume_version(
                self.local_user_id,
                {
                    "title": title,
                    "content": content,
                    "parent_resume_id": resume_id,
                    "version_label": metadata.get("version_label"),
                    "target_job_title": metadata.get("target_job_title"),
                    "application_id": application_id,
                    "status": resume_status,
                    "source_type": source_type,
                },
            )
            aggregate_type = "opportunity" if application_id is not None else "resume"
            aggregate_id = application_id if application_id is not None else new_id
            self._write_event(
                repository,
                aggregate_type,
                aggregate_id,
                "resume.version_created",
                self._agent_receipt_payload(
                    {
                        "resume_id": new_id,
                        "parent_resume_id": resume_id,
                        "version_label": metadata.get("version_label"),
                        "source_type": source_type,
                        "action_id": action_id,
                    },
                    source,
                    "resume",
                    new_id,
                    resume_status,
                ),
            )
            row = repository.owned("resumes", new_id, self.local_user_id)
        return dict(row)

    def create_action_item(
        self, user_id: int, values: dict[str, Any], source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        values = self._require_mapping(values, "action item values")
        permitted = {
            "opportunity_id",
            "application_id",
            "title",
            "type",
            "description",
            "status",
            "priority",
            "due_date",
            "due_at",
        }
        unknown = set(values) - permitted
        if unknown:
            raise ValueError(f"unknown action item fields: {', '.join(sorted(unknown))}")
        title = self._bounded_text(values.get("title"), "title", 500, required=True)
        action_type = self._bounded_text(values.get("type"), "type", 100)
        description = self._bounded_text(values.get("description"), "description", 20_000)
        status = values.get("status") or "pending"
        if status not in ACTION_STATUSES:
            raise ValueError("invalid action item status")
        source = self._bounded_text(source, "source", 100, required=True)
        application_id = values.get("opportunity_id", values.get("application_id"))
        due_at = values.get("due_date", values.get("due_at"))
        due_at = self._bounded_text(due_at, "due date", 100)
        priority = self._integer(values.get("priority", 0), "priority")
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            if application_id is not None and not repository.owned(
                "job_applications", application_id, self.local_user_id
            ):
                raise LookupError("opportunity not found")
            action_id = repository.add_action(
                self.local_user_id,
                {
                    "application_id": application_id,
                    "title": title,
                    "action_type": action_type,
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "due_at": due_at,
                    "source": source,
                },
            )
            aggregate_type = "opportunity" if application_id is not None else "action_item"
            aggregate_id = application_id if application_id is not None else action_id
            self._write_event(
                repository,
                aggregate_type,
                aggregate_id,
                "action_item.created",
                self._agent_receipt_payload(
                    {"action_id": action_id, "title": title, "type": action_type},
                    source,
                    "action_item",
                    action_id,
                    status,
                ),
            )
            row = repository.owned("action_items", action_id, self.local_user_id)
        return self._action_from_row(row)

    def list_action_items(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            rows = unit_of_work.career.list_actions(self.local_user_id)
        return [self._action_from_row(row) for row in rows]

    def complete_action_item(
        self, user_id: int, action_id: int, evidence: str = "", source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        evidence = self._bounded_text(evidence, "evidence", 20_000) or ""
        source = self._bounded_text(source, "source", 100, required=True)
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            row = repository.owned("action_items", action_id, self.local_user_id)
            if not row:
                raise LookupError("action item not found")
            changed = row["status"] != "completed"
            if changed:
                repository.complete_action(action_id, self.local_user_id, evidence)
            if changed or source.startswith("agent:"):
                aggregate_type = (
                    "opportunity" if row["application_id"] is not None else "action_item"
                )
                aggregate_id = (
                    row["application_id"] if row["application_id"] is not None else action_id
                )
                self._write_event(
                    repository,
                    aggregate_type,
                    aggregate_id,
                    "action_item.completed",
                    self._agent_receipt_payload(
                        {"action_id": action_id, "has_evidence": bool(evidence)},
                        source,
                        "action_item",
                        action_id,
                        "completed",
                    ),
                )
            row = repository.owned("action_items", action_id, self.local_user_id)
        return self._action_from_row(row)

    def save_report(
        self, user_id: int, values: dict[str, Any], source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        values = self._require_mapping(values, "report values")
        permitted = {
            "report_type",
            "title",
            "period_start",
            "period_end",
            "content",
            "status",
            "action_id",
        }
        unknown = set(values) - permitted
        if unknown:
            raise ValueError(f"unknown report fields: {', '.join(sorted(unknown))}")
        report_type = self._bounded_text(
            values.get("report_type"), "report_type", 100, required=True
        )
        title = self._bounded_text(values.get("title"), "title", 500)
        period_start = self._bounded_text(values.get("period_start"), "period_start", 100)
        period_end = self._bounded_text(values.get("period_end"), "period_end", 100)
        status = self._bounded_text(values.get("status", "ready"), "status", 50, required=True)
        if status not in {"draft", "ready", "archived"}:
            raise ValueError("invalid report status")
        content = values.get("content")
        if not isinstance(content, dict):
            raise ValueError("content must be an object")
        content_json = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        if len(content_json) > 200_000:
            raise ValueError("content is too large")
        source = self._bounded_text(source, "source", 100, required=True)
        action_id = values.get("action_id")
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            if action_id is not None:
                action_id = self._integer(action_id, "action_id")
                action = repository.owned("action_items", action_id, self.local_user_id)
                if not action:
                    raise LookupError("action item not found")
                if action["status"] != "pending":
                    raise ValueError("report action item is not pending")
                if action["action_type"] not in {"career_report", "save_career_report"}:
                    raise ValueError("action item is not a report action")
            report_id = repository.add_report(
                self.local_user_id,
                {
                    "report_type": report_type,
                    "title": title,
                    "period_start": period_start,
                    "period_end": period_end,
                    "content_json": content_json,
                    "status": status,
                },
            )
            self._write_event(
                repository,
                "career_report",
                report_id,
                "career_report.saved",
                self._agent_receipt_payload(
                    {"report_type": report_type, "action_id": action_id},
                    source,
                    "career_report",
                    report_id,
                    status,
                ),
            )
            row = repository.owned("career_reports", report_id, self.local_user_id)
        result = dict(row)
        result["content"] = json.loads(result.pop("content_json"))
        return result

    def get_report(self, user_id: int, report_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        report_id = self._integer(report_id, "report_id")
        with self._unit_of_work() as unit_of_work:
            row = unit_of_work.career.owned("career_reports", report_id, self.local_user_id)
            if row is None:
                raise LookupError("career report not found")
        result = dict(row)
        result["content"] = json.loads(result.pop("content_json"))
        return result

    def timeline(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.career
            if not repository.owned(
                "job_applications",
                opportunity_id,
                self.local_user_id,
                include_deleted=True,
            ):
                raise LookupError("opportunity not found")
            rows = repository.timeline(self.local_user_id, opportunity_id)
        return [self._event_from_row(row) for row in rows]

    def _write_event(
        self,
        repository,
        aggregate_type: str,
        aggregate_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        repository.events.add(
            self.local_user_id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload,
        )
        apply_event_to_actions(
            repository.events,
            self.local_user_id,
            event_type,
            aggregate_type,
            aggregate_id,
            payload,
        )

    @staticmethod
    def _agent_receipt_payload(
        payload: dict[str, Any],
        source: str,
        entity_type: str,
        entity_id: int,
        status: str | None = None,
    ) -> dict[str, Any]:
        result = {**payload, "source": source}
        if source.startswith("agent:"):
            parts = source.split(":", 2)
            if len(parts) != 3 or not parts[2]:
                raise ValueError("invalid agent receipt source")
            receipt = {
                "action_type": parts[2],
                "entity_type": entity_type,
                "id": entity_id,
            }
            if status is not None:
                receipt["status"] = status
            result["_agent_receipt"] = receipt
        return result

    @staticmethod
    def _compact_opportunity_payload(values: dict[str, Any], source: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "fields": sorted(set(values) - {"user_id", "created_by"}),
            "source": source,
        }
        for field in ("status", "company", "job_title"):
            if field in values:
                payload[field] = values[field]
        return payload


__all__ = [
    "ACTION_STATUSES",
    "ALLOWED_STATUS_TRANSITIONS",
    "CareerService",
    "DELIVERABLE_THRESHOLD",
    "JD_REQUIREMENT_MARKERS",
    "JD_RESPONSIBILITY_MARKERS",
    "MIN_JD_UNIQUE_CHARACTERS",
    "MIN_MEANINGFUL_JD_LENGTH",
    "POLISH_THRESHOLD",
    "READINESS_RECENT_LIMIT",
    "READINESS_WEIGHTS",
    "RESUME_SOURCE_TYPES",
    "RESUME_STATUSES",
    "is_meaningful_jd_snapshot",
]

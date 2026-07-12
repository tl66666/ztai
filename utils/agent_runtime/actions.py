from __future__ import annotations

import json
import math
import os
import threading
import uuid
from copy import deepcopy
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from utils.domain.career import (
    ACTION_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    RESUME_SOURCE_TYPES,
    RESUME_STATUSES,
    CareerService,
)
from utils.domain.database import APPLICATION_STATUSES, connect, migrate_database


ALLOWED_ACTION_TYPES = frozenset(
    {
        "set_career_goal",
        "create_opportunity",
        "create_resume_version",
        "link_opportunity_resume",
        "create_interview_plan",
        "create_action_item",
        "complete_action_item",
        "update_opportunity",
        "save_career_report",
    }
)
PROPOSAL_STATUSES = frozenset(
    {"pending", "executing", "completed", "cancelled", "expired", "failed"}
)
DEFAULT_EXPIRY_MINUTES = 30
EXECUTION_LEASE_SECONDS = 30

OPPORTUNITY_TEXT_LIMITS = {
    "company": 300,
    "job_title": 300,
    "status": 50,
    "city": 200,
    "notes": 20_000,
    "jd_text": 200_000,
    "source_url": 2_000,
    "channel": 200,
    "contact_name": 300,
    "contact_info": 2_000,
    "next_action_at": 100,
    "interview_at": 100,
    "deadline_at": 100,
    "rejection_reason": 5_000,
    "offer_details": 20_000,
}
OPPORTUNITY_FIELDS = frozenset(
    {*OPPORTUNITY_TEXT_LIMITS, "salary_min", "salary_max", "resume_id", "priority"}
)


def _schema_object(
    properties: dict[str, Any], required: tuple[str, ...] = ()
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _schema_text(limit: int, *, required: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "maxLength": limit}
    if required:
        schema["minLength"] = 1
    return schema


def _schema_integer(
    minimum: int | None = None, maximum: int | None = None
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "integer"}
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _opportunity_argument_properties() -> dict[str, Any]:
    properties = {
        field: _schema_text(limit, required=field in {"company", "job_title", "status"})
        for field, limit in OPPORTUNITY_TEXT_LIMITS.items()
    }
    properties["status"] = {
        "type": "string",
        "enum": list(APPLICATION_STATUSES),
    }
    properties.update(
        {
            "salary_min": _schema_integer(0, 1_000_000_000),
            "salary_max": _schema_integer(0, 1_000_000_000),
            "resume_id": _schema_integer(1),
            "priority": _schema_integer(-1000, 1000),
        }
    )
    return properties


def _career_action_argument_schemas() -> dict[str, dict[str, Any]]:
    string_list_200 = {
        "type": "array",
        "maxItems": 200,
        "items": _schema_text(500, required=True),
    }
    preference_list = {
        "type": "array",
        "maxItems": 50,
        "items": _schema_text(100, required=True),
    }
    profile = _schema_object(
        {
            "career_direction": _schema_text(10_000),
            "target_role": _schema_text(10_000),
            "cities": string_list_200,
            "salary": _schema_object(
                {
                    "min": _schema_integer(0, 1_000_000_000),
                    "max": _schema_integer(0, 1_000_000_000),
                    "currency": _schema_text(50, required=True),
                }
            ),
            "experience": _schema_text(10_000),
            "confirmed_skills": string_list_200,
            "preferences": _schema_object(
                {
                    "remote": {"type": "boolean"},
                    "hybrid": {"type": "boolean"},
                    "onsite": {"type": "boolean"},
                    "relocation": {"type": "boolean"},
                    "employment_types": preference_list,
                    "work_modes": preference_list,
                    "industries": preference_list,
                    "company_sizes": preference_list,
                }
            ),
            "constraints": string_list_200,
        }
    )
    profile["minProperties"] = 1

    metadata = _schema_object(
        {
            "version_label": _schema_text(300),
            "target_job_title": _schema_text(300),
            "application_id": _schema_integer(1),
            "status": {"type": "string", "enum": list(RESUME_STATUSES)},
            "source_type": {"type": "string", "enum": list(RESUME_SOURCE_TYPES)},
            "title": _schema_text(300),
            "action_id": _schema_integer(1),
        }
    )
    action_item_properties = {
        "opportunity_id": _schema_integer(1),
        "application_id": _schema_integer(1),
        "title": _schema_text(500, required=True),
        "type": _schema_text(100),
        "description": _schema_text(20_000),
        "status": {"type": "string", "enum": list(ACTION_STATUSES)},
        "priority": _schema_integer(-1000, 1000),
        "due_date": _schema_text(100),
        "due_at": _schema_text(100),
    }
    changes = _schema_object(_opportunity_argument_properties())
    changes["minProperties"] = 1
    report_content = {
        "type": "object",
        "maxProperties": 500,
        "x-maxDataDepth": 10,
        "propertyNames": {"type": "string", "minLength": 1, "maxLength": 200},
        "additionalProperties": {"$ref": "#/$defs/jsonValue"},
    }
    return {
        "set_career_goal": profile,
        "create_opportunity": _schema_object(
            _opportunity_argument_properties(), ("company", "job_title")
        ),
        "create_resume_version": _schema_object(
            {
                "resume_id": _schema_integer(1),
                "content": _schema_text(1_000_000, required=True),
                "metadata": metadata,
            },
            ("resume_id", "content", "metadata"),
        ),
        "link_opportunity_resume": _schema_object(
            {"opportunity_id": _schema_integer(1), "resume_id": _schema_integer(1)},
            ("opportunity_id", "resume_id"),
        ),
        "create_interview_plan": _schema_object(
            {
                "opportunity_id": _schema_integer(1),
                "title": _schema_text(500, required=True),
                "description": _schema_text(20_000),
                "due_at": _schema_text(100),
            },
            ("opportunity_id",),
        ),
        "create_action_item": _schema_object(action_item_properties, ("title",)),
        "complete_action_item": _schema_object(
            {"action_id": _schema_integer(1), "evidence": _schema_text(20_000)},
            ("action_id",),
        ),
        "update_opportunity": _schema_object(
            {"opportunity_id": _schema_integer(1), "changes": changes},
            ("opportunity_id", "changes"),
        ),
        "save_career_report": _schema_object(
            {
                "action_id": _schema_integer(1),
                "report_type": _schema_text(100, required=True),
                "title": _schema_text(500),
                "period_start": _schema_text(100),
                "period_end": _schema_text(100),
                "content": report_content,
                "status": {"type": "string", "enum": ["draft", "ready", "archived"]},
            },
            ("report_type", "content"),
        ),
    }


def career_action_tool_schema() -> dict[str, Any]:
    """Return the model-facing schema derived from canonical action validation."""
    rationale = _schema_text(1000)
    argument_schemas = _career_action_argument_schemas()
    branches = []
    for action_type in sorted(ALLOWED_ACTION_TYPES):
        branches.append(
            _schema_object(
                {
                    "action_type": {"const": action_type},
                    "arguments": argument_schemas[action_type],
                    "rationale": rationale,
                },
                ("action_type", "arguments"),
            )
        )
    schema = _schema_object(
        {
            "action_type": {"type": "string", "enum": sorted(ALLOWED_ACTION_TYPES)},
            "arguments": {"type": "object"},
            "rationale": rationale,
        },
        ("action_type", "arguments"),
    )
    schema["oneOf"] = branches
    schema["$defs"] = {
        "jsonValue": {
            "oneOf": [
                {"type": "null"},
                {"type": "boolean"},
                {
                    "type": "number",
                    "minimum": -1_000_000_000_000_000,
                    "maximum": 1_000_000_000_000_000,
                },
                {"type": "string", "maxLength": 20_000},
                {
                    "type": "array",
                    "maxItems": 500,
                    "items": {"$ref": "#/$defs/jsonValue"},
                },
                {
                    "type": "object",
                    "maxProperties": 500,
                    "propertyNames": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "additionalProperties": {"$ref": "#/$defs/jsonValue"},
                },
            ]
        }
    }
    return deepcopy(schema)

_LOCKS_GUARD = threading.Lock()
_PROPOSAL_LOCKS: dict[tuple[str, int], threading.Lock] = {}


class ActionProposalError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int = 409):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class ActionProposalService:
    def __init__(
        self,
        db_path: str | os.PathLike[str],
        career_service: CareerService | None = None,
        local_user_id: int = 1,
        claim_failpoint: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.db_path = os.fspath(db_path)
        self.local_user_id = int(local_user_id)
        migrate_database(self.db_path)
        self.career_service = career_service or CareerService(
            self.db_path, local_user_id=self.local_user_id
        )
        self._claim_failpoint = claim_failpoint

    def propose(
        self,
        user_id: int,
        action_type: str,
        arguments: dict[str, Any],
        rationale: str = "",
        agent_run_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        if action_type not in ALLOWED_ACTION_TYPES:
            raise ValueError("invalid action type")
        normalized = self._validate(action_type, arguments)
        rationale = self._sanitize_rationale(rationale)
        agent_run_id = self._text(agent_run_id, "agent_run_id", 200)
        preview = self._preview(action_type, normalized)
        risk_level = self._risk_level(action_type, normalized)
        expires_at = self._iso(self._now() + timedelta(minutes=DEFAULT_EXPIRY_MINUTES))
        idempotency_key = uuid.uuid4().hex
        serialized = self._json(normalized)
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_action_proposals (
                    user_id, agent_run_id, action_type, payload_json, arguments_json,
                    preview, rationale, status, risk_level, expires_at, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (
                    self.local_user_id, agent_run_id, action_type, serialized, serialized,
                    preview, rationale, risk_level, expires_at, idempotency_key,
                ),
            )
            proposal_id = cursor.lastrowid
        return self.get(user_id, proposal_id)

    def get(self, user_id: int, proposal_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        self._expire_pending(proposal_id)
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM agent_action_proposals WHERE id = ? AND user_id = ?",
                (proposal_id, self.local_user_id),
            ).fetchone()
            if row is None:
                exists = conn.execute(
                    "SELECT 1 FROM agent_action_proposals WHERE id = ?", (proposal_id,)
                ).fetchone()
                if exists:
                    raise PermissionError("proposal belongs to another user")
                raise LookupError("proposal not found")
        return self._from_row(row)

    def edit(
        self, user_id: int, proposal_id: int, allowed_changes: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        if not isinstance(allowed_changes, dict):
            raise ValueError("edit changes must be an object")
        self._validate_json_keys(allowed_changes, "edit changes")
        proposal = self.get(user_id, proposal_id)
        if proposal["status"] != "pending":
            raise self._state_error(proposal["status"])
        safe_fields = self._editable_fields(proposal["action_type"])
        if set(allowed_changes) - safe_fields:
            raise ValueError("edit contains fields that are not allowed")
        merged = dict(proposal["arguments"])
        if proposal["action_type"] == "update_opportunity":
            merged_changes = dict(merged["changes"])
            merged_changes.update(allowed_changes)
            merged["changes"] = merged_changes
        elif proposal["action_type"] == "create_resume_version" and "metadata" in allowed_changes:
            metadata_changes = allowed_changes["metadata"]
            if not isinstance(metadata_changes, dict):
                raise ValueError("edit metadata must be an object")
            if set(metadata_changes) - self._editable_resume_metadata_fields():
                raise ValueError("edit contains metadata fields that are not allowed")
            metadata = dict(merged.get("metadata", {}))
            metadata.update(metadata_changes)
            merged.update(
                {
                    field: value
                    for field, value in allowed_changes.items()
                    if field != "metadata"
                }
            )
            merged["metadata"] = metadata
        else:
            merged.update(allowed_changes)
        normalized = self._validate(proposal["action_type"], merged)
        serialized = self._json(normalized)
        preview = self._preview(proposal["action_type"], normalized)
        risk_level = self._risk_level(proposal["action_type"], normalized)
        with connect(self.db_path) as conn:
            updated = conn.execute(
                """
                UPDATE agent_action_proposals
                SET payload_json = ?, arguments_json = ?, preview = ?, risk_level = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (
                    serialized, serialized, preview, risk_level,
                    proposal_id, self.local_user_id,
                ),
            ).rowcount
        if updated != 1:
            raise ActionProposalError("invalid_state", "proposal is no longer pending")
        return self.get(user_id, proposal_id)

    def confirm(self, user_id: int, proposal_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        lock = self._proposal_lock(proposal_id)
        with lock:
            proposal = self.get(user_id, proposal_id)
            if proposal["status"] == "completed":
                return proposal
            receipt = self._receipt_result(proposal)
            if receipt is not None:
                self._finalize_or_uncertain(proposal_id, receipt)
                return self.get(user_id, proposal_id)
            if proposal["status"] == "pending":
                claimed = self._claim_pending(proposal_id)
            elif proposal["status"] == "executing":
                if not self._execution_is_stale(proposal.get("executing_at")):
                    raise self._state_error("executing")
                claimed = self._claim_stale_execution(
                    proposal_id, proposal.get("executing_at")
                )
            else:
                raise self._state_error(proposal["status"])
            if claimed is None:
                return self._resolve_competing_confirm(user_id, proposal_id)

            proposal = claimed

            source = self._receipt_source(proposal)
            try:
                result = self._execute(
                    proposal["action_type"], proposal["arguments"], source
                )
            except Exception as exc:
                receipt = self._receipt_result(proposal)
                if receipt is not None:
                    self._finalize_or_uncertain(proposal_id, receipt)
                    return self.get(user_id, proposal_id)
                self._mark_failed(proposal_id)
                raise ActionProposalError(
                    "execution_failed", "action execution failed", 500
                ) from exc

            self._finalize_or_uncertain(proposal_id, result)
            return self.get(user_id, proposal_id)

    def cancel(self, user_id: int, proposal_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        proposal = self.get(user_id, proposal_id)
        if proposal["status"] != "pending":
            raise self._state_error(proposal["status"])
        with connect(self.db_path) as conn:
            updated = conn.execute(
                """
                UPDATE agent_action_proposals
                SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP,
                    reviewed_by = 'local_user', reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (proposal_id, self.local_user_id),
            ).rowcount
        if updated != 1:
            raise ActionProposalError("invalid_state", "proposal is no longer pending")
        return self.get(user_id, proposal_id)

    def list_pending(self, user_id: int) -> list[dict[str, Any]]:
        return self.list_actions(user_id, status="pending")

    def list_actions(
        self, user_id: int, status: str | None = None
    ) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        self._expire_all_pending()
        if status is not None and status not in PROPOSAL_STATUSES:
            raise ValueError("invalid proposal status")
        where_status = " AND status = ?" if status is not None else ""
        parameters: tuple[Any, ...] = (
            (self.local_user_id, status) if status is not None else (self.local_user_id,)
        )
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM agent_action_proposals
                WHERE user_id = ?{where_status}
                ORDER BY created_at, id
                """,
                parameters,
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _execute(
        self, action_type: str, arguments: dict[str, Any], source: str
    ) -> dict[str, Any]:
        service = self.career_service
        user_id = self.local_user_id
        if action_type == "set_career_goal":
            entity = service.upsert_profile(user_id, arguments, source=source)
            return self._result("career_profile", entity)
        if action_type == "create_opportunity":
            entity = service.create_opportunity(user_id, arguments, source=source)
            return self._result("opportunity", entity)
        if action_type == "create_resume_version":
            entity = service.create_resume_version(
                user_id,
                arguments["resume_id"],
                arguments["content"],
                arguments["metadata"],
                source=source,
            )
            return self._result("resume", entity)
        if action_type == "link_opportunity_resume":
            entity = service.update_opportunity(
                user_id,
                arguments["opportunity_id"],
                {"resume_id": arguments["resume_id"]},
                source=source,
            )
            return self._result("opportunity", entity)
        if action_type == "create_interview_plan":
            values = {
                "opportunity_id": arguments["opportunity_id"],
                "title": arguments.get("title", "Prepare interview"),
                "description": arguments.get("description"),
                "due_at": arguments.get("due_at"),
                "type": "interview_plan",
            }
            entity = service.create_action_item(user_id, values, source=source)
            return self._result("action_item", entity)
        if action_type == "create_action_item":
            entity = service.create_action_item(user_id, arguments, source=source)
            return self._result("action_item", entity)
        if action_type == "complete_action_item":
            entity = service.complete_action_item(
                user_id,
                arguments["action_id"],
                arguments.get("evidence", ""),
                source=source,
            )
            return self._result("action_item", entity)
        if action_type == "update_opportunity":
            entity = service.update_opportunity(
                user_id, arguments["opportunity_id"], arguments["changes"], source=source
            )
            return self._result("opportunity", entity)
        if action_type == "save_career_report":
            entity = service.save_report(user_id, arguments, source=source)
            return self._result("career_report", entity)
        raise ValueError("invalid action type")

    def _validate(self, action_type: str, arguments: Any) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        self._validate_json_keys(arguments, "arguments")
        result = self._normalize(arguments)
        allowed = self._all_fields(action_type)
        unknown = set(result) - allowed
        if unknown:
            raise ValueError(f"unknown arguments: {', '.join(sorted(unknown))}")

        if action_type == "set_career_goal":
            if not result:
                raise ValueError("career goal requires at least one field")
            self._validate_profile_fields(result)
        elif action_type == "create_opportunity":
            self._required_text(result, "company", 300)
            self._required_text(result, "job_title", 300)
            self._validate_opportunity_fields(result)
            self._check_optional_owned(result, "resume_id", "resumes", "resume")
        elif action_type == "create_resume_version":
            self._required_id(result, "resume_id")
            self._required_text(result, "content", 1_000_000)
            if not isinstance(result.get("metadata"), dict):
                raise ValueError("metadata must be an object")
            self._validate_resume_metadata(result["metadata"])
            self._check_owned("resumes", result["resume_id"], "resume")
            application_id = result["metadata"].get("application_id")
            if application_id is not None:
                self._check_owned("job_applications", application_id, "opportunity", True)
            action_id = result["metadata"].get("action_id")
            if action_id is not None:
                with connect(self.db_path) as conn:
                    action = conn.execute(
                        """
                        SELECT action_type,status,application_id FROM action_items
                        WHERE id = ? AND user_id = ?
                        """,
                        (action_id, self.local_user_id),
                    ).fetchone()
                if action is None:
                    raise LookupError("action item not found")
                if action["status"] not in {"pending", "in_progress"}:
                    raise ValueError("resume action item is not active")
                if action["action_type"] not in {"create_resume_version", "resume_version"}:
                    raise ValueError("action item is not a resume version action")
                if application_id is None or action["application_id"] != application_id:
                    raise ValueError("resume action item opportunity does not match")
        elif action_type == "link_opportunity_resume":
            self._required_id(result, "opportunity_id")
            self._required_id(result, "resume_id")
            self._check_owned("job_applications", result["opportunity_id"], "opportunity", True)
            self._check_owned("resumes", result["resume_id"], "resume")
        elif action_type == "create_interview_plan":
            self._required_id(result, "opportunity_id")
            self._check_owned("job_applications", result["opportunity_id"], "opportunity", True)
            if "title" in result:
                self._required_text(result, "title", 500)
            for field in ("description", "due_at"):
                if field in result:
                    result[field] = self._text(
                        result[field], field, 20_000 if field == "description" else 100
                    )
        elif action_type == "create_action_item":
            self._required_text(result, "title", 500)
            self._validate_action_item_fields(result)
            opportunity_id = result.get("opportunity_id", result.get("application_id"))
            if opportunity_id is not None:
                self._check_owned("job_applications", opportunity_id, "opportunity", True)
        elif action_type == "complete_action_item":
            self._required_id(result, "action_id")
            if "evidence" in result:
                result["evidence"] = self._text(
                    result["evidence"], "evidence", 20_000
                )
            self._check_owned("action_items", result["action_id"], "action item")
        elif action_type == "update_opportunity":
            self._required_id(result, "opportunity_id")
            if not isinstance(result.get("changes"), dict) or not result["changes"]:
                raise ValueError("changes must be a non-empty object")
            self._check_owned("job_applications", result["opportunity_id"], "opportunity", True)
            self._validate_opportunity_fields(
                result["changes"], opportunity_id=result["opportunity_id"]
            )
            if "status" in result["changes"]:
                with connect(self.db_path) as conn:
                    current = conn.execute(
                        "SELECT status FROM job_applications WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
                        (result["opportunity_id"], self.local_user_id),
                    ).fetchone()
                allowed = ALLOWED_STATUS_TRANSITIONS.get(
                    current["status"], frozenset(APPLICATION_STATUSES)
                )
                if result["changes"]["status"] not in allowed:
                    raise ValueError("invalid status transition")
            self._check_optional_owned(result["changes"], "resume_id", "resumes", "resume")
        elif action_type == "save_career_report":
            if "action_id" in result:
                self._required_id(result, "action_id")
                with connect(self.db_path) as conn:
                    action = conn.execute(
                        """
                        SELECT action_type, status FROM action_items
                        WHERE id = ? AND user_id = ?
                        """,
                        (result["action_id"], self.local_user_id),
                    ).fetchone()
                if action is None:
                    raise LookupError("action item not found")
                if action["status"] != "pending":
                    raise ValueError("report action item is not pending")
                if action["action_type"] not in {"career_report", "save_career_report"}:
                    raise ValueError("action item is not a report action")
            self._required_text(result, "report_type", 100)
            if not isinstance(result.get("content"), dict):
                raise ValueError("content must be an object")
            self._validate_json_value(result["content"], "content")
            if len(self._json(result["content"])) > 200_000:
                raise ValueError("content is too large")
            for field, limit in (
                ("title", 500), ("period_start", 100), ("period_end", 100)
            ):
                if field in result:
                    result[field] = self._text(result[field], field, limit)
            status = result.get("status", "ready")
            if status not in {"draft", "ready", "archived"}:
                raise ValueError("invalid report status")
        return result

    @staticmethod
    def _all_fields(action_type: str) -> set[str]:
        return set(
            _career_action_argument_schemas()[action_type]["properties"]
        )

    def _editable_fields(self, action_type: str) -> set[str]:
        fields = {
            "set_career_goal": self._all_fields("set_career_goal"),
            "create_opportunity": self._all_fields("create_opportunity") - {"resume_id"},
            "create_resume_version": {"content", "metadata"},
            "link_opportunity_resume": set(),
            "create_interview_plan": {"title", "description", "due_at"},
            "create_action_item": {
                "title", "type", "description", "status", "priority", "due_date", "due_at"
            },
            "complete_action_item": {"evidence"},
            "update_opportunity": self._all_fields("create_opportunity") - {"resume_id"},
            "save_career_report": self._all_fields("save_career_report") - {"action_id"},
        }
        return fields[action_type]

    @staticmethod
    def _editable_resume_metadata_fields() -> set[str]:
        return {"version_label", "target_job_title", "status", "source_type", "title"}

    def _preview(self, action_type: str, arguments: dict[str, Any]) -> str:
        if action_type == "set_career_goal":
            return f"Update career goal fields: {', '.join(sorted(arguments))}"
        if action_type == "create_opportunity":
            preview = f"Create opportunity {arguments['company']} / {arguments['job_title']}"
            if arguments.get("resume_id") is not None:
                preview += f" using resume #{arguments['resume_id']}"
            return preview
        if action_type == "create_resume_version":
            label = arguments.get("metadata", {}).get("version_label") or "new version"
            preview = f"Create resume version {label} from resume #{arguments['resume_id']}"
            application_id = arguments.get("metadata", {}).get("application_id")
            if application_id is not None:
                preview += f" for application #{application_id}"
            return preview + " (content redacted)"
        if action_type == "link_opportunity_resume":
            return f"Link opportunity #{arguments['opportunity_id']} to resume #{arguments['resume_id']}"
        if action_type == "create_interview_plan":
            return f"Create interview preparation action for opportunity #{arguments['opportunity_id']}"
        if action_type == "create_action_item":
            preview = f"Create action item: {arguments['title']}"
            opportunity_id = arguments.get(
                "opportunity_id", arguments.get("application_id")
            )
            if opportunity_id is not None:
                preview += f" for opportunity #{opportunity_id}"
            return preview
        if action_type == "complete_action_item":
            return f"Complete action item #{arguments['action_id']}"
        if action_type == "update_opportunity":
            fields = ", ".join(sorted(arguments["changes"]))
            preview = f"Update opportunity #{arguments['opportunity_id']} fields: {fields}"
            if arguments["changes"].get("resume_id") is not None:
                preview += f" using resume #{arguments['changes']['resume_id']}"
            return preview + " (sensitive values redacted)"
        return f"Save {arguments['report_type']} career report (content redacted)"

    @staticmethod
    def _risk_level(action_type: str, arguments: dict[str, Any]) -> str:
        if action_type in {"complete_action_item", "update_opportunity", "link_opportunity_resume"}:
            return "high" if action_type == "update_opportunity" and "status" in arguments.get("changes", {}) else "medium"
        if action_type in {"create_opportunity", "create_resume_version", "set_career_goal"}:
            return "medium"
        return "low"

    def _expire_pending(self, proposal_id: int) -> None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT expires_at FROM agent_action_proposals WHERE id = ? AND user_id = ? AND status = 'pending'",
                (proposal_id, self.local_user_id),
            ).fetchone()
            if row and self._is_expired(row["expires_at"]):
                conn.execute(
                    """
                    UPDATE agent_action_proposals
                    SET status = 'expired', expired_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'pending'
                    """,
                    (proposal_id, self.local_user_id),
                )

    def _expire_all_pending(self) -> None:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, expires_at FROM agent_action_proposals WHERE user_id = ? AND status = 'pending'",
                (self.local_user_id,),
            ).fetchall()
            expired_ids = [row["id"] for row in rows if self._is_expired(row["expires_at"])]
            if expired_ids:
                placeholders = ",".join("?" for _ in expired_ids)
                conn.execute(
                    f"UPDATE agent_action_proposals SET status = 'expired', expired_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders}) AND user_id = ? AND status = 'pending'",
                    (*expired_ids, self.local_user_id),
                )

    def _proposal_lock(self, proposal_id: int) -> threading.Lock:
        key = (os.path.abspath(self.db_path), int(proposal_id))
        with _LOCKS_GUARD:
            return _PROPOSAL_LOCKS.setdefault(key, threading.Lock())

    def _claim_pending(self, proposal_id: int) -> dict[str, Any] | None:
        executing_at = self._iso(self._now())
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_action_proposals WHERE id = ? AND user_id = ?",
                (proposal_id, self.local_user_id),
            ).fetchone()
            if row is None or row["status"] != "pending":
                return None
            updated = conn.execute(
                """
                UPDATE agent_action_proposals
                SET status = 'executing', reviewed_by = 'local_user',
                    reviewed_at = ?, executing_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (executing_at, executing_at, proposal_id, self.local_user_id),
            ).rowcount
            if updated != 1:
                return None
            claimed = dict(row)
            claimed.update(
                status="executing",
                reviewed_by="local_user",
                reviewed_at=executing_at,
                executing_at=executing_at,
            )
            proposal = self._from_row(claimed)
            if self._claim_failpoint is not None:
                self._claim_failpoint(proposal)
            return proposal

    def _claim_stale_execution(
        self, proposal_id: int, previous_executing_at: str | None
    ) -> dict[str, Any] | None:
        executing_at = self._iso(self._now())
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_action_proposals WHERE id = ? AND user_id = ?",
                (proposal_id, self.local_user_id),
            ).fetchone()
            if (
                row is None
                or row["status"] != "executing"
                or row["executing_at"] != previous_executing_at
            ):
                return None
            if previous_executing_at is None:
                updated = conn.execute(
                    """
                    UPDATE agent_action_proposals
                    SET executing_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'executing'
                      AND executing_at IS NULL
                    """,
                    (executing_at, proposal_id, self.local_user_id),
                ).rowcount
            else:
                updated = conn.execute(
                    """
                    UPDATE agent_action_proposals
                    SET executing_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'executing'
                      AND executing_at = ?
                    """,
                    (
                        executing_at,
                        proposal_id,
                        self.local_user_id,
                        previous_executing_at,
                    ),
                ).rowcount
            if updated != 1:
                return None
            claimed = dict(row)
            claimed["executing_at"] = executing_at
            proposal = self._from_row(claimed)
            if self._claim_failpoint is not None:
                self._claim_failpoint(proposal)
            return proposal

    def _resolve_competing_confirm(
        self, user_id: int, proposal_id: int
    ) -> dict[str, Any]:
        proposal = self.get(user_id, proposal_id)
        if proposal["status"] == "completed":
            return proposal
        receipt = self._receipt_result(proposal)
        if receipt is not None:
            self._finalize_or_uncertain(proposal_id, receipt)
            return self.get(user_id, proposal_id)
        raise self._state_error(proposal["status"])

    def _receipt_source(self, proposal: dict[str, Any]) -> str:
        key = str(proposal["idempotency_key"] or "").strip().lower()
        if len(key) != 32 or any(char not in "0123456789abcdef" for char in key):
            raise ValueError("invalid proposal idempotency key")
        return f"agent:{key}:{proposal['action_type']}"

    def _receipt_result(self, proposal: dict[str, Any]) -> dict[str, Any] | None:
        source = self._receipt_source(proposal)
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM domain_events
                WHERE user_id = ? AND source = ?
                """,
                (self.local_user_id, source),
            ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt is invalid", 500
            ) from exc
        receipt = payload.get("_agent_receipt")
        if not isinstance(receipt, dict) or receipt.get("action_type") != proposal["action_type"]:
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt is invalid", 500
            )
        result = {
            "entity_type": receipt.get("entity_type"),
            "id": receipt.get("id"),
        }
        if "status" in receipt:
            result["status"] = receipt["status"]
        self._verify_receipt_owner(result)
        return result

    def _verify_receipt_owner(self, result: dict[str, Any]) -> None:
        tables = {
            "career_profile": "career_profiles",
            "opportunity": "job_applications",
            "resume": "resumes",
            "action_item": "action_items",
            "career_report": "career_reports",
        }
        table = tables.get(result.get("entity_type"))
        entity_id = result.get("id")
        if table is None or not isinstance(entity_id, int):
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt is invalid", 500
            )
        with connect(self.db_path) as conn:
            owned = conn.execute(
                f"SELECT 1 FROM {table} WHERE id = ? AND user_id = ?",
                (entity_id, self.local_user_id),
            ).fetchone()
        if owned is None:
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt target is unavailable", 500
            )

    def _finalize_completed(
        self, proposal_id: int, result: dict[str, Any]
    ) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE agent_action_proposals
                SET status = 'completed', result_json = ?, error_code = NULL,
                    executed_at = COALESCE(executed_at, CURRENT_TIMESTAMP),
                    completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status IN ('executing', 'completed')
                """,
                (self._json(result), proposal_id, self.local_user_id),
            )

    def _finalize_or_uncertain(
        self, proposal_id: int, result: dict[str, Any]
    ) -> None:
        try:
            self._finalize_completed(proposal_id, result)
        except Exception as exc:
            raise ActionProposalError(
                "execution_uncertain",
                "action execution status is uncertain; retry confirmation",
                500,
            ) from exc

    def _mark_failed(self, proposal_id: int) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE agent_action_proposals
                SET status = 'failed', error_code = 'execution_failed',
                    failed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'executing'
                """,
                (proposal_id, self.local_user_id),
            )

    def _execution_is_stale(self, value: str | None) -> bool:
        if not value:
            return True
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return True
        return (self._now() - parsed).total_seconds() >= EXECUTION_LEASE_SECONDS

    def _check_optional_owned(self, values, field, table, label):
        if values.get(field) is not None:
            self._check_owned(table, values[field], label, table == "job_applications")

    def _check_owned(self, table: str, row_id: Any, label: str, active_only: bool = False):
        row_id = self._integer(row_id, label)
        deleted = " AND deleted_at IS NULL" if active_only else ""
        with connect(self.db_path) as conn:
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE id = ? AND user_id = ?{deleted}",
                (row_id, self.local_user_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"{label} not found")

    def _validate_opportunity_fields(
        self, values: dict[str, Any], opportunity_id: int | None = None
    ) -> None:
        if not isinstance(values, dict):
            raise ValueError("opportunity fields must be an object")
        unknown = set(values) - OPPORTUNITY_FIELDS
        if unknown:
            raise ValueError(f"unknown opportunity fields: {', '.join(sorted(unknown))}")
        for field, limit in OPPORTUNITY_TEXT_LIMITS.items():
            if field not in values:
                continue
            required = field in {"company", "job_title", "status"}
            values[field] = self._text(values[field], field, limit, required=required)
        if "status" in values and values["status"] not in APPLICATION_STATUSES:
            raise ValueError("invalid application status")
        for field in ("salary_min", "salary_max", "resume_id", "priority"):
            if field in values and values[field] is not None:
                values[field] = self._integer(values[field], field)
        if values.get("resume_id") is not None and values["resume_id"] <= 0:
            raise ValueError("resume_id must be positive")
        for field in ("salary_min", "salary_max"):
            if values.get(field) is not None and not 0 <= values[field] <= 1_000_000_000:
                raise ValueError(f"{field} is out of range")
        if values.get("priority") is not None and not -1000 <= values["priority"] <= 1000:
            raise ValueError("priority is out of range")
        salary_min = values.get("salary_min")
        salary_max = values.get("salary_max")
        if opportunity_id is not None and (salary_min is None or salary_max is None):
            with connect(self.db_path) as conn:
                current = conn.execute(
                    """
                    SELECT salary_min, salary_max FROM job_applications
                    WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                    """,
                    (opportunity_id, self.local_user_id),
                ).fetchone()
            salary_min = values.get("salary_min", current["salary_min"])
            salary_max = values.get("salary_max", current["salary_max"])
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise ValueError("salary_min cannot exceed salary_max")

    def _validate_profile_fields(self, values: dict[str, Any]) -> None:
        for field in ("career_direction", "target_role", "experience"):
            if field in values:
                values[field] = self._text(values[field], field, 10_000)
        for field in ("cities", "confirmed_skills", "constraints"):
            if field in values:
                if not isinstance(values[field], list) or len(values[field]) > 200:
                    raise ValueError(f"{field} must be a list with at most 200 items")
                values[field] = [
                    self._text(item, field, 500, required=True) for item in values[field]
                ]
        for field in ("salary", "preferences"):
            if field in values:
                if not isinstance(values[field], dict):
                    raise ValueError(f"{field} must be an object")
                if len(self._json(values[field])) > 20_000:
                    raise ValueError(f"{field} is too large")
        if "salary" in values:
            salary = values["salary"]
            unknown = set(salary) - {"min", "max", "currency"}
            if unknown:
                raise ValueError(f"unknown salary fields: {', '.join(sorted(unknown))}")
            for field in ("min", "max"):
                if salary.get(field) is not None:
                    salary[field] = self._integer(salary[field], f"salary.{field}")
                    if not 0 <= salary[field] <= 1_000_000_000:
                        raise ValueError(f"salary.{field} is out of range")
            if "currency" in salary:
                salary["currency"] = self._text(
                    salary["currency"], "salary.currency", 50, required=True
                )
            if salary.get("min") is not None and salary.get("max") is not None:
                if salary["min"] > salary["max"]:
                    raise ValueError("salary.min cannot exceed salary.max")
        if "preferences" in values:
            preferences = values["preferences"]
            allowed = {
                "remote",
                "hybrid",
                "onsite",
                "relocation",
                "employment_types",
                "work_modes",
                "industries",
                "company_sizes",
            }
            unknown = set(preferences) - allowed
            if unknown:
                raise ValueError(
                    f"unknown preference fields: {', '.join(sorted(unknown))}"
                )
            for field in ("remote", "hybrid", "onsite", "relocation"):
                if field in preferences and not isinstance(preferences[field], bool):
                    raise ValueError(f"preferences.{field} must be a boolean")
            for field in (
                "employment_types", "work_modes", "industries", "company_sizes"
            ):
                if field in preferences:
                    value = preferences[field]
                    if not isinstance(value, list) or len(value) > 50:
                        raise ValueError(
                            f"preferences.{field} must be a list with at most 50 items"
                        )
                    preferences[field] = [
                        self._text(
                            item,
                            f"preferences.{field}",
                            100,
                            required=True,
                        )
                        for item in value
                    ]

    def _validate_resume_metadata(self, metadata: dict[str, Any]) -> None:
        permitted = {
            "version_label", "target_job_title", "application_id", "status",
            "source_type", "title", "action_id",
        }
        unknown = set(metadata) - permitted
        if unknown:
            raise ValueError(f"unknown resume metadata: {', '.join(sorted(unknown))}")
        for field in ("version_label", "target_job_title", "title"):
            if field in metadata:
                metadata[field] = self._text(metadata[field], field, 300)
        if metadata.get("status", "active") not in RESUME_STATUSES:
            raise ValueError("invalid resume status")
        if metadata.get("source_type", "manual") not in RESUME_SOURCE_TYPES:
            raise ValueError("invalid source_type")
        if metadata.get("application_id") is not None:
            metadata["application_id"] = self._integer(
                metadata["application_id"], "application_id"
            )
            if metadata["application_id"] <= 0:
                raise ValueError("application_id must be positive")
        if metadata.get("action_id") is not None:
            metadata["action_id"] = self._integer(metadata["action_id"], "action_id")
            if metadata["action_id"] <= 0:
                raise ValueError("action_id must be positive")

    def _validate_action_item_fields(self, values: dict[str, Any]) -> None:
        if values.get("status", "pending") not in ACTION_STATUSES:
            raise ValueError("invalid action item status")
        for field, limit in (("type", 100), ("description", 20_000), ("due_date", 100), ("due_at", 100)):
            if field in values:
                values[field] = self._text(values[field], field, limit)
        if "priority" in values:
            values["priority"] = self._integer(values["priority"], "priority")
            if not -1000 <= values["priority"] <= 1000:
                raise ValueError("priority is out of range")
        for field in ("opportunity_id", "application_id"):
            if values.get(field) is not None:
                self._required_id(values, field)
                self._check_owned(
                    "job_applications", values[field], "opportunity", True
                )
        if (
            values.get("opportunity_id") is not None
            and values.get("application_id") is not None
            and values["opportunity_id"] != values["application_id"]
        ):
            raise ValueError("opportunity_id and application_id must match")
        if (
            values.get("due_date") is not None
            and values.get("due_at") is not None
            and values["due_date"] != values["due_at"]
        ):
            raise ValueError("due_date and due_at must match")

    def _required_id(self, values: dict[str, Any], field: str):
        if field not in values:
            raise ValueError(f"{field} is required")
        values[field] = self._integer(values[field], field)
        if values[field] <= 0:
            raise ValueError(f"{field} must be positive")

    def _validate_json_value(
        self, value: Any, name: str, depth: int = 0
    ) -> None:
        if depth > 10:
            raise ValueError(f"{name} is too deeply nested")
        if value is None or isinstance(value, bool):
            return
        if isinstance(value, str):
            if len(value) > 20_000:
                raise ValueError(f"{name} string exceeds 20000 characters")
            return
        if isinstance(value, int):
            if abs(value) > 1_000_000_000_000_000:
                raise ValueError(f"{name} number is out of range")
            return
        if isinstance(value, float):
            if not math.isfinite(value) or abs(value) > 1_000_000_000_000_000:
                raise ValueError(f"{name} number is out of range")
            return
        if isinstance(value, list):
            if len(value) > 500:
                raise ValueError(f"{name} list has too many items")
            for index, item in enumerate(value):
                self._validate_json_value(item, f"{name}[{index}]", depth + 1)
            return
        if isinstance(value, dict):
            if len(value) > 500:
                raise ValueError(f"{name} object has too many fields")
            for key, item in value.items():
                if not isinstance(key, str) or not key or len(key) > 200:
                    raise ValueError(f"{name} has an invalid field name")
                self._validate_json_value(item, f"{name}.{key}", depth + 1)
            return
        raise ValueError(f"{name} contains an unsupported value")

    def _validate_json_keys(self, value: Any, name: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{name} has an invalid field name")
                self._validate_json_keys(item, f"{name}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._validate_json_keys(item, f"{name}[{index}]")

    def _required_text(self, values: dict[str, Any], field: str, limit: int):
        values[field] = self._text(values.get(field), field, limit, required=True)

    @staticmethod
    def _text(value: Any, name: str, limit: int, required: bool = False) -> str | None:
        if value is None:
            if required:
                raise ValueError(f"{name} is required")
            return None
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text")
        value = value.strip()
        if required and not value:
            raise ValueError(f"{name} is required")
        if len(value) > limit:
            raise ValueError(f"{name} exceeds {limit} characters")
        return value

    @staticmethod
    def _integer(value: Any, name: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        raise ValueError(f"{name} must be an integer")

    def _normalize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, str):
            return value.strip()
        return value

    @staticmethod
    def _result(entity_type: str, entity: dict[str, Any]) -> dict[str, Any]:
        result = {"entity_type": entity_type, "id": entity.get("id")}
        if "status" in entity:
            result["status"] = entity["status"]
        return result

    @staticmethod
    def _from_row(row) -> dict[str, Any]:
        result = dict(row)
        arguments_json = result.pop("arguments_json", None) or result.get("payload_json") or "{}"
        result.pop("payload_json", None)
        result["arguments"] = json.loads(arguments_json)
        result["result"] = json.loads(result.pop("result_json")) if result.get("result_json") else None
        return result

    def public(self, proposal: dict[str, Any]) -> dict[str, Any]:
        arguments = proposal.get("arguments") or {}
        editable = self._public_editable_values(proposal["action_type"], arguments)
        target_ids: dict[str, int] = {}

        def collect_targets(value: Any) -> None:
            if not isinstance(value, dict):
                return
            for key, item in value.items():
                if (
                    key.endswith("_id")
                    and isinstance(item, int)
                    and not isinstance(item, bool)
                ):
                    target_ids[key] = item
                elif isinstance(item, dict):
                    collect_targets(item)

        collect_targets(arguments)
        fields = (
            "id", "action_type", "preview", "status", "risk_level", "created_at",
            "updated_at", "expires_at", "reviewed_at", "executing_at", "executed_at",
            "completed_at", "cancelled_at", "expired_at", "failed_at", "error_code",
        )
        public = {field: proposal.get(field) for field in fields}
        public["target_ids"] = target_ids
        public["editable"] = editable
        public["result"] = proposal.get("result")
        return public

    @staticmethod
    def _public_editable_values(
        action_type: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        safe_fields = {
            "set_career_goal": {
                "career_direction", "target_role", "cities", "salary", "experience"
            },
            "create_opportunity": {
                "company", "job_title", "status", "city", "salary_min", "salary_max",
                "priority", "channel", "source_url", "next_action_at", "interview_at",
                "deadline_at",
            },
            "create_resume_version": {"metadata"},
            "link_opportunity_resume": set(),
            "create_interview_plan": {"title", "due_at"},
            "create_action_item": {
                "title", "type", "status", "priority", "due_date", "due_at"
            },
            "complete_action_item": set(),
            "update_opportunity": set(),
            "save_career_report": {
                "report_type", "title", "period_start", "period_end", "status"
            },
        }[action_type]
        if action_type == "update_opportunity":
            return ActionProposalService._public_editable_values(
                "create_opportunity", arguments.get("changes", {})
            )
        if action_type == "create_resume_version":
            metadata = arguments.get("metadata") or {}
            permitted = {
                "version_label", "target_job_title", "status", "source_type", "title"
            }
            return {
                "metadata": {key: metadata[key] for key in permitted if key in metadata}
            }
        return {key: arguments[key] for key in safe_fields if key in arguments}

    @staticmethod
    def _state_error(status: str) -> ActionProposalError:
        codes = {
            "cancelled": "proposal_cancelled",
            "expired": "proposal_expired",
            "executing": "proposal_executing",
            "failed": "proposal_failed",
            "completed": "proposal_completed",
        }
        return ActionProposalError(codes.get(status, "invalid_state"), f"proposal is {status}")

    def _require_local_user(self, user_id: int) -> None:
        if int(user_id) != self.local_user_id:
            raise PermissionError("operation is restricted to the local user")

    @staticmethod
    def _json(value: Any) -> str:
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("value must be valid JSON") from exc

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat()

    def _is_expired(self, value: str | None) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed <= self._now()
        except (TypeError, ValueError):
            return True

    def _sanitize_rationale(self, value: Any) -> str:
        text = self._text(value, "rationale", 1000) or ""
        return " ".join("".join(char for char in text if char.isprintable()).split())


__all__ = [
    "ALLOWED_ACTION_TYPES",
    "ActionProposalError",
    "ActionProposalService",
    "career_action_tool_schema",
    "DEFAULT_EXPIRY_MINUTES",
    "EXECUTION_LEASE_SECONDS",
    "PROPOSAL_STATUSES",
]

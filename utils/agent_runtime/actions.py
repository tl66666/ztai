from __future__ import annotations

import json
import os
import threading
import uuid
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
    ):
        self.db_path = os.fspath(db_path)
        self.local_user_id = int(local_user_id)
        migrate_database(self.db_path)
        self.career_service = career_service or CareerService(
            self.db_path, local_user_id=self.local_user_id
        )

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
            metadata = dict(merged.get("metadata", {}))
            metadata.update(allowed_changes["metadata"])
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
            if proposal["status"] != "pending":
                raise self._state_error(proposal["status"])
            with connect(self.db_path) as conn:
                claimed = conn.execute(
                    """
                    UPDATE agent_action_proposals
                    SET status = 'executing', reviewed_by = 'local_user',
                        reviewed_at = CURRENT_TIMESTAMP, executing_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'pending'
                    """,
                    (proposal_id, self.local_user_id),
                ).rowcount
            if claimed != 1:
                raise ActionProposalError("proposal_executing", "proposal is executing")

            try:
                result = self._execute(proposal["action_type"], proposal["arguments"])
            except Exception as exc:
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
                raise ActionProposalError(
                    "execution_failed", f"action execution failed: {exc}", 422
                ) from exc

            with connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE agent_action_proposals
                    SET status = 'completed', result_json = ?, error_code = NULL,
                        executed_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ? AND status = 'executing'
                    """,
                    (self._json(result), proposal_id, self.local_user_id),
                )
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
        self._require_local_user(user_id)
        self._expire_all_pending()
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_action_proposals
                WHERE user_id = ? AND status = 'pending'
                ORDER BY created_at, id
                """,
                (self.local_user_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _execute(self, action_type: str, arguments: dict[str, Any]) -> dict[str, Any]:
        service = self.career_service
        user_id = self.local_user_id
        if action_type == "set_career_goal":
            entity = service.upsert_profile(user_id, arguments, source="agent")
            return self._result("career_profile", entity)
        if action_type == "create_opportunity":
            entity = service.create_opportunity(user_id, arguments, source="agent")
            return self._result("opportunity", entity)
        if action_type == "create_resume_version":
            entity = service.create_resume_version(
                user_id, arguments["resume_id"], arguments["content"], arguments["metadata"]
            )
            return self._result("resume", entity)
        if action_type == "link_opportunity_resume":
            entity = service.update_opportunity(
                user_id,
                arguments["opportunity_id"],
                {"resume_id": arguments["resume_id"]},
                source="agent",
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
            entity = service.create_action_item(user_id, values, source="agent")
            return self._result("action_item", entity)
        if action_type == "create_action_item":
            entity = service.create_action_item(user_id, arguments, source="agent")
            return self._result("action_item", entity)
        if action_type == "complete_action_item":
            entity = service.complete_action_item(
                user_id, arguments["action_id"], arguments.get("evidence", "")
            )
            return self._result("action_item", entity)
        if action_type == "update_opportunity":
            entity = service.update_opportunity(
                user_id, arguments["opportunity_id"], arguments["changes"], source="agent"
            )
            return self._result("opportunity", entity)
        if action_type == "save_career_report":
            entity = service.save_report(user_id, arguments, source="agent")
            return self._result("career_report", entity)
        raise ValueError("invalid action type")

    def _validate(self, action_type: str, arguments: Any) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
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
            self._check_owned("action_items", result["action_id"], "action item")
        elif action_type == "update_opportunity":
            self._required_id(result, "opportunity_id")
            if not isinstance(result.get("changes"), dict) or not result["changes"]:
                raise ValueError("changes must be a non-empty object")
            self._validate_opportunity_fields(result["changes"])
            self._check_owned("job_applications", result["opportunity_id"], "opportunity", True)
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
            self._required_text(result, "report_type", 100)
            if not isinstance(result.get("content"), dict):
                raise ValueError("content must be an object")
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
        fields = {
            "set_career_goal": {"career_direction", "target_role", "cities", "salary", "experience", "confirmed_skills", "preferences", "constraints", "source_metadata"},
            "create_opportunity": {"company", "job_title", "status", "city", "salary_min", "salary_max", "notes", "jd_text", "source_url", "channel", "resume_id", "priority", "contact_name", "contact_info", "next_action_at", "interview_at", "deadline_at", "rejection_reason", "offer_details"},
            "create_resume_version": {"resume_id", "content", "metadata"},
            "link_opportunity_resume": {"opportunity_id", "resume_id"},
            "create_interview_plan": {"opportunity_id", "title", "description", "due_at"},
            "create_action_item": {"opportunity_id", "application_id", "title", "type", "description", "status", "priority", "due_date", "due_at"},
            "complete_action_item": {"action_id", "evidence"},
            "update_opportunity": {"opportunity_id", "changes"},
            "save_career_report": {"report_type", "title", "period_start", "period_end", "content", "status"},
        }
        return fields[action_type]

    def _editable_fields(self, action_type: str) -> set[str]:
        fields = self._all_fields(action_type)
        if action_type == "update_opportunity":
            return self._all_fields("create_opportunity")
        return fields - {"resume_id", "opportunity_id", "application_id", "action_id"}

    def _preview(self, action_type: str, arguments: dict[str, Any]) -> str:
        if action_type == "set_career_goal":
            return f"Update career goal fields: {', '.join(sorted(arguments))}"
        if action_type == "create_opportunity":
            return f"Create opportunity {arguments['company']} / {arguments['job_title']}"
        if action_type == "create_resume_version":
            label = arguments.get("metadata", {}).get("version_label") or "new version"
            return f"Create resume version {label} from resume #{arguments['resume_id']} (content redacted)"
        if action_type == "link_opportunity_resume":
            return f"Link opportunity #{arguments['opportunity_id']} to resume #{arguments['resume_id']}"
        if action_type == "create_interview_plan":
            return f"Create interview preparation action for opportunity #{arguments['opportunity_id']}"
        if action_type == "create_action_item":
            return f"Create action item: {arguments['title']}"
        if action_type == "complete_action_item":
            return f"Complete action item #{arguments['action_id']}"
        if action_type == "update_opportunity":
            fields = ", ".join(sorted(arguments["changes"]))
            return f"Update opportunity #{arguments['opportunity_id']} fields: {fields} (sensitive values redacted)"
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

    def _validate_opportunity_fields(self, values: dict[str, Any]):
        if "status" in values and values["status"] not in APPLICATION_STATUSES:
            raise ValueError("invalid application status")
        for field in ("salary_min", "salary_max", "resume_id", "priority"):
            if field in values and values[field] is not None:
                values[field] = self._integer(values[field], field)
        if values.get("salary_min") is not None and values.get("salary_max") is not None:
            if values["salary_min"] > values["salary_max"]:
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
        for field in ("salary", "preferences", "source_metadata"):
            if field in values:
                if not isinstance(values[field], dict):
                    raise ValueError(f"{field} must be an object")
                if len(self._json(values[field])) > 20_000:
                    raise ValueError(f"{field} is too large")

    def _validate_resume_metadata(self, metadata: dict[str, Any]) -> None:
        permitted = {
            "version_label", "target_job_title", "application_id", "status",
            "source_type", "title",
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

    def _validate_action_item_fields(self, values: dict[str, Any]) -> None:
        if values.get("status", "pending") not in ACTION_STATUSES:
            raise ValueError("invalid action item status")
        for field, limit in (("type", 100), ("description", 20_000), ("due_date", 100), ("due_at", 100)):
            if field in values:
                values[field] = self._text(values[field], field, limit)
        if "priority" in values:
            values["priority"] = self._integer(values["priority"], "priority")

    def _required_id(self, values: dict[str, Any], field: str):
        if field not in values:
            raise ValueError(f"{field} is required")
        values[field] = self._integer(values[field], field)
        if values[field] <= 0:
            raise ValueError(f"{field} must be positive")

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
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc

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
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

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
    "DEFAULT_EXPIRY_MINUTES",
    "PROPOSAL_STATUSES",
]

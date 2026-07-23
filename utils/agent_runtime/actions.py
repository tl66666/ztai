from __future__ import annotations

import json
import os
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.adapters.persistence.sqlalchemy.agent_action_store import (
    SqlAlchemyAgentActionStore,
)
from backend.adapters.persistence.sqlalchemy.agent_session import (
    AgentSessionProvider,
    SessionFactory,
)
from utils.agent_runtime.action_execution import ActionExecutionMixin
from utils.agent_runtime.action_presentation import ActionPresentationMixin
from utils.agent_runtime.action_schema import (
    ALLOWED_ACTION_TYPES,
    DEFAULT_EXPIRY_MINUTES,
    EXECUTION_LEASE_SECONDS,
    PROPOSAL_STATUSES,
    career_action_tool_schema,
)
from utils.agent_runtime.action_validation import ActionValidationMixin
from utils.domain.career import CareerService

_LOCKS_GUARD = threading.Lock()
_PROPOSAL_LOCKS: dict[tuple[str, int], threading.Lock] = {}


class ActionProposalError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int = 409):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class ActionProposalService(ActionValidationMixin, ActionExecutionMixin, ActionPresentationMixin):
    def __init__(
        self,
        db_path: str | os.PathLike[str],
        career_service: CareerService | None = None,
        local_user_id: int = 1,
        claim_failpoint: Callable[[dict[str, Any]], None] | None = None,
        session_factory: SessionFactory | None = None,
    ):
        self.db_path = os.fspath(db_path)
        self.local_user_id = int(local_user_id)
        self.career_service = career_service or CareerService(
            self.db_path, local_user_id=self.local_user_id
        )
        self._claim_failpoint = claim_failpoint
        self._sessions = AgentSessionProvider(
            self.db_path,
            session_factory=session_factory,
        )
        self._persistence = SqlAlchemyAgentActionStore(self._sessions)

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
        proposal_id = self._persistence.insert_proposal(
            {
                "user_id": self.local_user_id,
                "agent_run_id": agent_run_id,
                "action_type": action_type,
                "payload_json": serialized,
                "arguments_json": serialized,
                "preview": preview,
                "rationale": rationale,
                "status": "pending",
                "risk_level": risk_level,
                "expires_at": expires_at,
                "idempotency_key": idempotency_key,
            }
        )
        return self.get(user_id, proposal_id)

    def get(self, user_id: int, proposal_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        self._expire_pending(proposal_id)
        row, missing_globally = self._persistence.proposal(
            proposal_id,
            self.local_user_id,
        )
        if row is None:
            if not missing_globally:
                raise PermissionError("proposal belongs to another user")
            raise LookupError("proposal not found")
        return self._from_row(row)

    def draft(self, user_id: int, proposal_id: int) -> dict[str, Any]:
        """Return an owned, pending resume draft for explicit user review only."""
        proposal = self.get(user_id, proposal_id)
        if proposal["action_type"] != "create_resume_version":
            raise ActionProposalError(
                "draft_not_available", "this proposal does not contain a resume draft", 400
            )
        if proposal["status"] != "pending":
            raise self._state_error(proposal["status"])
        arguments = proposal.get("arguments") or {}
        metadata = arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else {}
        return {
            "proposal_id": proposal["id"],
            "resume_id": arguments.get("resume_id"),
            "content": arguments.get("content", ""),
            "metadata": metadata,
            "status": proposal["status"],
        }

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
                {field: value for field, value in allowed_changes.items() if field != "metadata"}
            )
            merged["metadata"] = metadata
        else:
            merged.update(allowed_changes)
        normalized = self._validate(proposal["action_type"], merged)
        serialized = self._json(normalized)
        preview = self._preview(proposal["action_type"], normalized)
        risk_level = self._risk_level(proposal["action_type"], normalized)
        updated = self._persistence.edit_proposal(
            proposal_id,
            self.local_user_id,
            {
                "payload_json": serialized,
                "arguments_json": serialized,
                "preview": preview,
                "risk_level": risk_level,
                "updated_at": self._iso(self._now()),
            },
        )
        if not updated:
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
                claimed = self._claim_stale_execution(proposal_id, proposal.get("executing_at"))
            else:
                raise self._state_error(proposal["status"])
            if claimed is None:
                return self._resolve_competing_confirm(user_id, proposal_id)

            proposal = claimed

            source = self._receipt_source(proposal)
            try:
                result = self._execute(proposal["action_type"], proposal["arguments"], source)
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
        updated = self._persistence.cancel_proposal(
            proposal_id,
            self.local_user_id,
            self._iso(self._now()),
        )
        if not updated:
            raise ActionProposalError("invalid_state", "proposal is no longer pending")
        return self.get(user_id, proposal_id)

    def list_pending(self, user_id: int) -> list[dict[str, Any]]:
        return self.list_actions(user_id, status="pending")

    def list_actions(self, user_id: int, status: str | None = None) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        self._expire_all_pending()
        if status is not None and status not in PROPOSAL_STATUSES:
            raise ValueError("invalid proposal status")
        rows = self._persistence.list_proposals(self.local_user_id, status)
        return [self._from_row(row) for row in rows]

    def _expire_pending(self, proposal_id: int) -> None:
        rows = self._persistence.pending_expiries(
            self.local_user_id,
            proposal_id,
        )
        expired_ids = [int(row["id"]) for row in rows if self._is_expired(row["expires_at"])]
        self._persistence.expire(
            self.local_user_id,
            expired_ids,
            self._iso(self._now()),
        )

    def _expire_all_pending(self) -> None:
        rows = self._persistence.pending_expiries(self.local_user_id)
        expired_ids = [int(row["id"]) for row in rows if self._is_expired(row["expires_at"])]
        self._persistence.expire(
            self.local_user_id,
            expired_ids,
            self._iso(self._now()),
        )

    def _proposal_lock(self, proposal_id: int) -> threading.Lock:
        key = (os.path.abspath(self.db_path), int(proposal_id))
        with _LOCKS_GUARD:
            return _PROPOSAL_LOCKS.setdefault(key, threading.Lock())

    def _claim_pending(self, proposal_id: int) -> dict[str, Any] | None:
        executing_at = self._iso(self._now())
        claimed = self._persistence.claim_pending(
            proposal_id,
            self.local_user_id,
            executing_at,
        )
        if claimed is None:
            return None
        proposal = self._from_row(claimed)
        if self._claim_failpoint is not None:
            self._claim_failpoint(proposal)
        return proposal

    def _claim_stale_execution(
        self, proposal_id: int, previous_executing_at: str | None
    ) -> dict[str, Any] | None:
        executing_at = self._iso(self._now())
        claimed = self._persistence.claim_stale(
            proposal_id,
            self.local_user_id,
            previous_executing_at,
            executing_at,
        )
        if claimed is None:
            return None
        proposal = self._from_row(claimed)
        if self._claim_failpoint is not None:
            self._claim_failpoint(proposal)
        return proposal

    def _resolve_competing_confirm(self, user_id: int, proposal_id: int) -> dict[str, Any]:
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
        payload_json = self._persistence.receipt_payload(
            self.local_user_id,
            source,
        )
        if payload_json is None:
            return None
        try:
            payload = json.loads(payload_json or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt is invalid", 500
            ) from exc
        receipt = payload.get("_agent_receipt")
        if not isinstance(receipt, dict) or receipt.get("action_type") != proposal["action_type"]:
            raise ActionProposalError("invalid_receipt", "agent execution receipt is invalid", 500)
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
            raise ActionProposalError("invalid_receipt", "agent execution receipt is invalid", 500)
        if not self._persistence.owned(
            table,
            entity_id,
            self.local_user_id,
            False,
        ):
            raise ActionProposalError(
                "invalid_receipt", "agent execution receipt target is unavailable", 500
            )

    def _finalize_completed(self, proposal_id: int, result: dict[str, Any]) -> None:
        self._persistence.finalize_completed(
            proposal_id,
            self.local_user_id,
            self._json(result),
            self._iso(self._now()),
        )

    def _finalize_or_uncertain(self, proposal_id: int, result: dict[str, Any]) -> None:
        try:
            self._finalize_completed(proposal_id, result)
        except Exception as exc:
            raise ActionProposalError(
                "execution_uncertain",
                "action execution status is uncertain; retry confirmation",
                500,
            ) from exc

    def _mark_failed(self, proposal_id: int) -> None:
        self._persistence.mark_failed(
            proposal_id,
            self.local_user_id,
            self._iso(self._now()),
        )

    def _execution_is_stale(self, value: str | None) -> bool:
        if not value:
            return True
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            return True
        return (self._now() - parsed).total_seconds() >= EXECUTION_LEASE_SECONDS

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
        return datetime.now(UTC)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat()

    def _is_expired(self, value: str | None) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
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

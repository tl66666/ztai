from __future__ import annotations

import json
from typing import Any


class ActionPresentationMixin:
    @staticmethod
    def _from_row(row) -> dict[str, Any]:
        result = dict(row)
        arguments_json = result.pop("arguments_json", None) or result.get("payload_json") or "{}"
        result.pop("payload_json", None)
        result["arguments"] = json.loads(arguments_json)
        result["result"] = (
            json.loads(result.pop("result_json")) if result.get("result_json") else None
        )
        return result

    def public(self, proposal: dict[str, Any]) -> dict[str, Any]:
        arguments = proposal.get("arguments") or {}
        editable = self._public_editable_values(proposal["action_type"], arguments)
        target_ids: dict[str, int] = {}

        def collect_targets(value: Any) -> None:
            if not isinstance(value, dict):
                return
            for key, item in value.items():
                if key.endswith("_id") and isinstance(item, int) and not isinstance(item, bool):
                    target_ids[key] = item
                elif isinstance(item, dict):
                    collect_targets(item)

        collect_targets(arguments)
        fields = (
            "id",
            "action_type",
            "preview",
            "status",
            "risk_level",
            "created_at",
            "updated_at",
            "expires_at",
            "reviewed_at",
            "executing_at",
            "executed_at",
            "completed_at",
            "cancelled_at",
            "expired_at",
            "failed_at",
            "error_code",
        )
        public = {field: proposal.get(field) for field in fields}
        public["target_ids"] = target_ids
        public["editable"] = editable
        public["result"] = proposal.get("result")
        return public

    @staticmethod
    def _public_editable_values(action_type: str, arguments: dict[str, Any]) -> dict[str, Any]:
        safe_fields = {
            "set_career_goal": {
                "career_direction",
                "target_role",
                "cities",
                "salary",
                "experience",
            },
            "create_opportunity": {
                "company",
                "job_title",
                "status",
                "city",
                "salary_min",
                "salary_max",
                "priority",
                "channel",
                "source_url",
                "next_action_at",
                "interview_at",
                "deadline_at",
            },
            "create_resume_version": {"metadata"},
            "link_opportunity_resume": set(),
            "create_interview_plan": {"title", "due_at"},
            "create_action_item": {"title", "type", "status", "priority", "due_date", "due_at"},
            "complete_action_item": set(),
            "update_opportunity": set(),
            "save_career_report": {"report_type", "title", "period_start", "period_end", "status"},
        }[action_type]
        if action_type == "update_opportunity":
            return ActionPresentationMixin._public_editable_values(
                "create_opportunity", arguments.get("changes", {})
            )
        if action_type == "create_resume_version":
            return {}
        return {key: arguments[key] for key in safe_fields if key in arguments}

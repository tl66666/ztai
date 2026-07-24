from __future__ import annotations

import math
from typing import Any

from utils.domain.career import (
    ACTION_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    RESUME_SOURCE_TYPES,
    RESUME_STATUSES,
)
from utils.domain.database import APPLICATION_STATUSES

from .action_schema import (
    OPPORTUNITY_FIELDS,
    OPPORTUNITY_TEXT_LIMITS,
    _career_action_argument_schemas,
)


class ActionValidationMixin:
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
                action = self._persistence.action_item(
                    action_id,
                    self.local_user_id,
                )
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
                result["evidence"] = self._text(result["evidence"], "evidence", 20_000)
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
                current_status = self._persistence.opportunity_status(
                    result["opportunity_id"],
                    self.local_user_id,
                )
                allowed = ALLOWED_STATUS_TRANSITIONS.get(
                    current_status,
                    frozenset(APPLICATION_STATUSES),
                )
                if result["changes"]["status"] not in allowed:
                    raise ValueError("invalid status transition")
            self._check_optional_owned(result["changes"], "resume_id", "resumes", "resume")
        elif action_type == "save_career_report":
            if "action_id" in result:
                self._required_id(result, "action_id")
                action = self._persistence.action_item(
                    result["action_id"],
                    self.local_user_id,
                )
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
            for field, limit in (("title", 500), ("period_start", 100), ("period_end", 100)):
                if field in result:
                    result[field] = self._text(result[field], field, limit)
            status = result.get("status", "ready")
            if status not in {"draft", "ready", "archived"}:
                raise ValueError("invalid report status")
        return result

    @staticmethod
    def _all_fields(action_type: str) -> set[str]:
        return set(_career_action_argument_schemas()[action_type]["properties"])

    def _editable_fields(self, action_type: str) -> set[str]:
        fields = {
            "set_career_goal": self._all_fields("set_career_goal"),
            "create_opportunity": self._all_fields("create_opportunity") - {"resume_id"},
            "create_resume_version": {"content", "metadata"},
            "link_opportunity_resume": set(),
            "create_interview_plan": {"title", "description", "due_at"},
            "create_action_item": {
                "title",
                "type",
                "description",
                "status",
                "priority",
                "due_date",
                "due_at",
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
            return "更新求职目标信息"
        if action_type == "create_opportunity":
            return f"新增投递：{arguments['company']} / {arguments['job_title']}"
        if action_type == "create_resume_version":
            label = arguments.get("metadata", {}).get("version_label") or "优化版"
            return f"将创建新简历版本「{label}」"
        if action_type == "link_opportunity_resume":
            return "将简历关联到当前投递机会"
        if action_type == "create_interview_plan":
            return "为当前机会创建面试准备任务"
        if action_type == "create_action_item":
            return f"新增行动任务：{arguments['title']}"
        if action_type == "complete_action_item":
            return "将行动任务标记为已完成"
        if action_type == "update_opportunity":
            return "更新当前投递信息"
        return "保存求职复盘报告"

    @staticmethod
    def _risk_level(action_type: str, arguments: dict[str, Any]) -> str:
        if action_type in {"complete_action_item", "update_opportunity", "link_opportunity_resume"}:
            return (
                "high"
                if action_type == "update_opportunity" and "status" in arguments.get("changes", {})
                else "medium"
            )
        if action_type in {"create_opportunity", "create_resume_version", "set_career_goal"}:
            return "medium"
        return "low"

    def _check_optional_owned(self, values, field, table, label):
        if values.get(field) is not None:
            self._check_owned(table, values[field], label, table == "job_applications")

    def _check_owned(self, table: str, row_id: Any, label: str, active_only: bool = False):
        row_id = self._integer(row_id, label)
        if not self._persistence.owned(
            table,
            row_id,
            self.local_user_id,
            active_only,
        ):
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
            current = self._persistence.opportunity_salary(
                opportunity_id,
                self.local_user_id,
            )
            if current is None:
                raise LookupError("opportunity not found")
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
                raise ValueError(f"unknown preference fields: {', '.join(sorted(unknown))}")
            for field in ("remote", "hybrid", "onsite", "relocation"):
                if field in preferences and not isinstance(preferences[field], bool):
                    raise ValueError(f"preferences.{field} must be a boolean")
            for field in ("employment_types", "work_modes", "industries", "company_sizes"):
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
        for field in ("version_label", "target_job_title", "title"):
            if field in metadata:
                metadata[field] = self._text(metadata[field], field, 300)
        if metadata.get("status", "active") not in RESUME_STATUSES:
            raise ValueError("invalid resume status")
        if metadata.get("source_type", "manual") not in RESUME_SOURCE_TYPES:
            raise ValueError("invalid source_type")
        if metadata.get("application_id") is not None:
            metadata["application_id"] = self._integer(metadata["application_id"], "application_id")
            if metadata["application_id"] <= 0:
                raise ValueError("application_id must be positive")
        if metadata.get("action_id") is not None:
            metadata["action_id"] = self._integer(metadata["action_id"], "action_id")
            if metadata["action_id"] <= 0:
                raise ValueError("action_id must be positive")

    def _validate_action_item_fields(self, values: dict[str, Any]) -> None:
        if values.get("status", "pending") not in ACTION_STATUSES:
            raise ValueError("invalid action item status")
        for field, limit in (
            ("type", 100),
            ("description", 20_000),
            ("due_date", 100),
            ("due_at", 100),
        ):
            if field in values:
                values[field] = self._text(values[field], field, limit)
        if "priority" in values:
            values["priority"] = self._integer(values["priority"], "priority")
            if not -1000 <= values["priority"] <= 1000:
                raise ValueError("priority is out of range")
        for field in ("opportunity_id", "application_id"):
            if values.get(field) is not None:
                self._required_id(values, field)
                self._check_owned("job_applications", values[field], "opportunity", True)
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

    def _validate_json_value(self, value: Any, name: str, depth: int = 0) -> None:
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

from __future__ import annotations

import json
from typing import Any

from .database import APPLICATION_STATUSES

_OPPORTUNITY_FIELDS = (
    "company",
    "job_title",
    "status",
    "city",
    "salary_min",
    "salary_max",
    "notes",
    "jd_text",
    "source_url",
    "channel",
    "resume_id",
    "priority",
    "contact_name",
    "contact_info",
    "next_action_at",
    "interview_at",
    "deadline_at",
    "rejection_reason",
    "offer_details",
)
_FIELD_LIMITS = {
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


class CareerDtoMixin:
    def _require_local_user(self, user_id: int) -> None:
        if user_id != self.local_user_id:
            raise PermissionError("operation is restricted to the local user")

    @staticmethod
    def _require_mapping(value: Any, name: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        return dict(value)

    @staticmethod
    def _bounded_text(value: Any, name: str, limit: int, required: bool = False) -> str | None:
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
    def _integer(value: Any, name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc

    def _validate_opportunity_values(
        self, values: dict[str, Any], creating: bool
    ) -> dict[str, Any]:
        values = self._require_mapping(values, "opportunity values")
        unknown = set(values) - set(_OPPORTUNITY_FIELDS)
        if unknown:
            raise ValueError(f"unknown opportunity fields: {', '.join(sorted(unknown))}")
        result = dict(values)
        if creating:
            result["user_id"] = self.local_user_id
            result["company"] = self._bounded_text(
                result.get("company"), "company", 300, required=True
            )
            result["job_title"] = self._bounded_text(
                result.get("job_title"), "job_title", 300, required=True
            )
        else:
            for required_field in ("company", "job_title"):
                if required_field in result:
                    result[required_field] = self._bounded_text(
                        result[required_field], required_field, 300, required=True
                    )
        for field, limit in _FIELD_LIMITS.items():
            if field in result and field not in {"company", "job_title", "status"}:
                result[field] = self._bounded_text(result[field], field, limit)
        if "status" in result:
            status = self._bounded_text(result["status"], "status", 50, required=True)
            if status not in APPLICATION_STATUSES:
                raise ValueError("invalid application status")
            result["status"] = status
        for field in ("salary_min", "salary_max", "resume_id", "priority"):
            if field in result:
                result[field] = self._integer(result[field], field)
        if result.get("salary_min") is not None and result.get("salary_max") is not None:
            if result["salary_min"] > result["salary_max"]:
                raise ValueError("salary_min cannot exceed salary_max")
        return result

    @staticmethod
    def _empty_profile() -> dict[str, Any]:
        return {
            "career_direction": "",
            "target_role": "",
            "cities": [],
            "salary": {},
            "experience": "",
            "confirmed_skills": [],
            "preferences": {},
            "constraints": [],
            "source_metadata": {},
        }

    def _merge_profile(
        self, current: dict[str, Any], values: dict[str, Any], source: str
    ) -> dict[str, Any]:
        permitted = set(self._empty_profile())
        unknown = set(values) - permitted
        if unknown:
            raise ValueError(f"unknown profile fields: {', '.join(sorted(unknown))}")
        merged = {**current, **values}
        for field in ("career_direction", "target_role", "experience"):
            merged[field] = self._bounded_text(merged.get(field), field, 10_000) or ""
        for field in ("cities", "confirmed_skills", "constraints"):
            if not isinstance(merged.get(field), list) or len(merged[field]) > 200:
                raise ValueError(f"{field} must be a list with at most 200 items")
            merged[field] = [
                self._bounded_text(item, field, 500, required=True) for item in merged[field]
            ]
        for field in ("salary", "preferences", "source_metadata"):
            if not isinstance(merged.get(field), dict):
                raise ValueError(f"{field} must be an object")
            if len(json.dumps(merged[field], ensure_ascii=False)) > 20_000:
                raise ValueError(f"{field} is too large")
        merged["source_metadata"] = {**merged["source_metadata"], "source": source}
        return merged

    @staticmethod
    def _serialize_profile(profile: dict[str, Any]) -> tuple[str, str, str, str, str]:
        target = {
            "target_role": profile["target_role"],
            "cities": profile["cities"],
            "salary": profile["salary"],
        }
        preferences = {
            "preferences": profile["preferences"],
            "constraints": profile["constraints"],
            "source_metadata": profile["source_metadata"],
        }
        return (
            profile["career_direction"],
            profile["experience"],
            json.dumps(target, ensure_ascii=False),
            json.dumps(profile["confirmed_skills"], ensure_ascii=False),
            json.dumps(preferences, ensure_ascii=False),
        )

    def _profile_from_row(self, row) -> dict[str, Any]:
        target = self._json_object(row["target_roles_json"])
        preferences = self._json_object(row["preferences_json"])
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "career_direction": row["headline"] or "",
            "target_role": target.get("target_role", ""),
            "cities": target.get("cities", []),
            "salary": target.get("salary", {}),
            "experience": row["summary"] or "",
            "confirmed_skills": self._json_list(row["skills_json"]),
            "preferences": preferences.get("preferences", {}),
            "constraints": preferences.get("constraints", []),
            "source_metadata": preferences.get("source_metadata", {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _json_object(value: str | None) -> dict[str, Any]:
        try:
            parsed = json.loads(value or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _json_list(value: str | None) -> list[Any]:
        try:
            parsed = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def _opportunity_from_row(row) -> dict[str, Any]:
        result = dict(row)
        result["needs_status_review"] = result.get("status") not in APPLICATION_STATUSES
        return result

    @staticmethod
    def _action_from_row(row) -> dict[str, Any]:
        result = dict(row)
        result["opportunity_id"] = result.get("application_id")
        result["type"] = result.get("action_type")
        result["due_date"] = result.get("due_at")
        return result

    @staticmethod
    def _event_from_row(row) -> dict[str, Any]:
        result = dict(row)
        try:
            result["payload"] = json.loads(result.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            result["payload"] = {}
            result.pop("payload_json", None)
        return result

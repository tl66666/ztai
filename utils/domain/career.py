from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from .database import APPLICATION_STATUSES, connect, ensure_column


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


class CareerService:
    def __init__(self, db_path: str | os.PathLike[str], local_user_id: int = 1):
        self.db_path = os.fspath(db_path)
        self.local_user_id = int(local_user_id)
        with connect(self.db_path) as conn:
            ensure_column(conn, "action_items", "action_type", "TEXT")
            ensure_column(conn, "action_items", "completion_evidence", "TEXT")
            ensure_column(conn, "job_applications", "deleted_at", "TEXT")

    def get_profile(self, user_id: int) -> dict[str, Any] | None:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM career_profiles WHERE user_id = ?", (self.local_user_id,)
            ).fetchone()
        return self._profile_from_row(row) if row else None

    def upsert_profile(
        self, user_id: int, values: dict[str, Any], source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        values = self._require_mapping(values, "profile values")
        source = self._bounded_text(source, "source", 100, required=True)
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM career_profiles WHERE user_id = ?", (self.local_user_id,)
            ).fetchone()
            current = self._profile_from_row(existing) if existing else self._empty_profile()
            merged = self._merge_profile(current, values, source)
            serialized = self._serialize_profile(merged)
            if existing:
                conn.execute(
                    """
                    UPDATE career_profiles
                    SET headline = ?, summary = ?, target_roles_json = ?, skills_json = ?,
                        preferences_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (*serialized, self.local_user_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO career_profiles (
                        user_id, headline, summary, target_roles_json, skills_json, preferences_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (self.local_user_id, *serialized),
                )
            self._write_event(
                conn,
                "profile",
                self.local_user_id,
                "profile.updated",
                {"fields": sorted(values), "source": source},
            )
            row = conn.execute(
                "SELECT * FROM career_profiles WHERE user_id = ?", (self.local_user_id,)
            ).fetchone()
        return self._profile_from_row(row)

    def list_opportunities(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_applications
                WHERE user_id = ? AND deleted_at IS NULL
                ORDER BY updated_at DESC, id DESC
                """,
                (self.local_user_id,),
            ).fetchall()
        return [self._opportunity_from_row(row) for row in rows]

    def get_opportunity(self, user_id: int, opportunity_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            row = self._owned_opportunity(conn, opportunity_id)
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
        columns = [*values]
        placeholders = ", ".join("?" for _ in columns)
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if values.get("resume_id") is not None and not self._owned_row(
                conn, "resumes", values["resume_id"]
            ):
                raise LookupError("resume not found")
            cursor = conn.execute(
                f"INSERT INTO job_applications ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(values[column] for column in columns),
            )
            opportunity_id = cursor.lastrowid
            self._write_event(
                conn,
                "opportunity",
                opportunity_id,
                "opportunity.created",
                self._compact_opportunity_payload(values, source),
            )
            row = self._owned_opportunity(conn, opportunity_id)
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
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = self._owned_opportunity(conn, opportunity_id)
            if not existing:
                raise LookupError("opportunity not found")
            merged_salary_min = changes.get("salary_min", existing["salary_min"])
            merged_salary_max = changes.get("salary_max", existing["salary_max"])
            if merged_salary_min is not None and merged_salary_max is not None:
                if merged_salary_min > merged_salary_max:
                    raise ValueError("salary_min cannot exceed salary_max")
            if changes.get("resume_id") is not None and not self._owned_row(
                conn, "resumes", changes["resume_id"]
            ):
                raise LookupError("resume not found")
            if "status" in changes:
                allowed = ALLOWED_STATUS_TRANSITIONS.get(existing["status"], frozenset(APPLICATION_STATUSES))
                if changes["status"] not in allowed:
                    raise ValueError("invalid status transition")
            changes = {
                field: value for field, value in changes.items() if existing[field] != value
            }
            if changes:
                assignments = ", ".join(f"{column} = ?" for column in changes)
                conn.execute(
                    f"UPDATE job_applications SET {assignments}, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND user_id = ?",
                    (*changes.values(), opportunity_id, self.local_user_id),
                )
                self._write_event(
                    conn,
                    "opportunity",
                    opportunity_id,
                    "opportunity.updated",
                    self._compact_opportunity_payload(changes, source),
                )
            row = self._owned_opportunity(conn, opportunity_id)
        return self._opportunity_from_row(row)

    def delete_opportunity(
        self, user_id: int, opportunity_id: int, source: str = "user"
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        source = self._bounded_text(source, "source", 100, required=True)
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = self._owned_opportunity(conn, opportunity_id)
            if not existing:
                raise LookupError("opportunity not found")
            self._write_event(
                conn,
                "opportunity",
                opportunity_id,
                "opportunity.deleted",
                {"source": source},
            )
            conn.execute(
                """
                UPDATE job_applications
                SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                """,
                (opportunity_id, self.local_user_id),
            )
            row = self._owned_row(conn, "job_applications", opportunity_id)
        return self._opportunity_from_row(row)

    def create_resume_version(
        self,
        user_id: int,
        resume_id: int,
        content: str,
        metadata: dict[str, Any],
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
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            source = self._owned_row(conn, "resumes", resume_id)
            if not source:
                raise LookupError("resume not found")
            application_id = metadata.get("application_id")
            if application_id is not None and not self._owned_opportunity(conn, application_id):
                raise LookupError("opportunity not found")
            title = metadata.get("title") or metadata.get("version_label") or source["title"]
            cursor = conn.execute(
                """
                INSERT INTO resumes (
                    user_id, title, content, parent_resume_id, version_label,
                    target_job_title, application_id, status, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.local_user_id,
                    title,
                    content,
                    resume_id,
                    metadata.get("version_label"),
                    metadata.get("target_job_title"),
                    application_id,
                    resume_status,
                    source_type,
                ),
            )
            new_id = cursor.lastrowid
            aggregate_type = "opportunity" if application_id is not None else "resume"
            aggregate_id = application_id if application_id is not None else new_id
            self._write_event(
                conn,
                aggregate_type,
                aggregate_id,
                "resume.version_created",
                {
                    "resume_id": new_id,
                    "parent_resume_id": resume_id,
                    "version_label": metadata.get("version_label"),
                    "source_type": source_type,
                },
            )
            row = self._owned_row(conn, "resumes", new_id)
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
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if application_id is not None and not self._owned_opportunity(conn, application_id):
                raise LookupError("opportunity not found")
            cursor = conn.execute(
                """
                INSERT INTO action_items (
                    user_id, application_id, title, action_type, description,
                    status, priority, due_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.local_user_id,
                    application_id,
                    title,
                    action_type,
                    description,
                    status,
                    priority,
                    due_at,
                    source,
                ),
            )
            action_id = cursor.lastrowid
            aggregate_type = "opportunity" if application_id is not None else "action_item"
            aggregate_id = application_id if application_id is not None else action_id
            self._write_event(
                conn,
                aggregate_type,
                aggregate_id,
                "action_item.created",
                {"action_id": action_id, "title": title, "type": action_type, "source": source},
            )
            row = self._owned_row(conn, "action_items", action_id)
        return self._action_from_row(row)

    def list_action_items(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM action_items WHERE user_id = ? ORDER BY due_at, id DESC",
                (self.local_user_id,),
            ).fetchall()
        return [self._action_from_row(row) for row in rows]

    def complete_action_item(
        self, user_id: int, action_id: int, evidence: str = ""
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        evidence = self._bounded_text(evidence, "evidence", 20_000) or ""
        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = self._owned_row(conn, "action_items", action_id)
            if not row:
                raise LookupError("action item not found")
            if row["status"] != "completed":
                conn.execute(
                    """
                    UPDATE action_items
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                        completion_evidence = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                    """,
                    (evidence, action_id, self.local_user_id),
                )
                aggregate_type = "opportunity" if row["application_id"] is not None else "action_item"
                aggregate_id = row["application_id"] if row["application_id"] is not None else action_id
                self._write_event(
                    conn,
                    aggregate_type,
                    aggregate_id,
                    "action_item.completed",
                    {"action_id": action_id, "has_evidence": bool(evidence)},
                )
            row = self._owned_row(conn, "action_items", action_id)
        return self._action_from_row(row)

    def timeline(self, user_id: int, opportunity_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            if not self._owned_row(conn, "job_applications", opportunity_id):
                raise LookupError("opportunity not found")
            rows = conn.execute(
                """
                SELECT * FROM domain_events
                WHERE user_id = ? AND aggregate_type = 'opportunity' AND aggregate_id = ?
                ORDER BY occurred_at, id
                """,
                (self.local_user_id, str(opportunity_id)),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

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

    def _validate_opportunity_values(self, values: dict[str, Any], creating: bool) -> dict[str, Any]:
        values = self._require_mapping(values, "opportunity values")
        unknown = set(values) - set(_OPPORTUNITY_FIELDS)
        if unknown:
            raise ValueError(f"unknown opportunity fields: {', '.join(sorted(unknown))}")
        result = dict(values)
        if creating:
            result["user_id"] = self.local_user_id
            result["company"] = self._bounded_text(result.get("company"), "company", 300, required=True)
            result["job_title"] = self._bounded_text(result.get("job_title"), "job_title", 300, required=True)
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

    def _merge_profile(self, current: dict[str, Any], values: dict[str, Any], source: str) -> dict[str, Any]:
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
            merged[field] = [self._bounded_text(item, field, 500, required=True) for item in merged[field]]
        for field in ("salary", "preferences", "source_metadata"):
            if not isinstance(merged.get(field), dict):
                raise ValueError(f"{field} must be an object")
            if len(json.dumps(merged[field], ensure_ascii=False)) > 20_000:
                raise ValueError(f"{field} is too large")
        merged["source_metadata"] = {**merged["source_metadata"], "source": source}
        return merged

    @staticmethod
    def _serialize_profile(profile: dict[str, Any]) -> tuple[str, str, str, str, str]:
        target = {"target_role": profile["target_role"], "cities": profile["cities"], "salary": profile["salary"]}
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

    def _profile_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
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
    def _opportunity_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["needs_status_review"] = result.get("status") not in APPLICATION_STATUSES
        return result

    @staticmethod
    def _action_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["opportunity_id"] = result.get("application_id")
        result["type"] = result.get("action_type")
        result["due_date"] = result.get("due_at")
        return result

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        try:
            result["payload"] = json.loads(result.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            result["payload"] = {}
            result.pop("payload_json", None)
        return result

    def _owned_row(self, conn: sqlite3.Connection, table: str, row_id: int) -> sqlite3.Row | None:
        return conn.execute(
            f"SELECT * FROM {table} WHERE id = ? AND user_id = ?",
            (row_id, self.local_user_id),
        ).fetchone()

    def _owned_opportunity(
        self, conn: sqlite3.Connection, opportunity_id: int
    ) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT * FROM job_applications
            WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (opportunity_id, self.local_user_id),
        ).fetchone()

    def _write_event(
        self,
        conn: sqlite3.Connection,
        aggregate_type: str,
        aggregate_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO domain_events (
                user_id, aggregate_type, aggregate_id, event_type, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.local_user_id,
                aggregate_type,
                str(aggregate_id),
                event_type,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _compact_opportunity_payload(values: dict[str, Any], source: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"fields": sorted(set(values) - {"user_id", "created_by"}), "source": source}
        for field in ("status", "company", "job_title"):
            if field in values:
                payload[field] = values[field]
        return payload


__all__ = [
    "ACTION_STATUSES",
    "ALLOWED_STATUS_TRANSITIONS",
    "CareerService",
    "RESUME_SOURCE_TYPES",
    "RESUME_STATUSES",
]

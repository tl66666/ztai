from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
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

# Readiness is a deterministic local heuristic. Counts only provide the small
# confidence bonuses below; evidence quality remains the dominant input.
READINESS_WEIGHTS = {
    "resume": 25,
    "alignment": 20,
    "interview": 25,
    "practice": 15,
    "pipeline": 15,
}
READINESS_RECENT_LIMIT = 5
REAL_JD_MIN_LENGTH = 12
DELIVERABLE_THRESHOLD = 70
POLISH_THRESHOLD = 42


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

    def calculate_readiness(self, user_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            resume = self._readiness_resume(conn)
            matches = self._readiness_matches(conn)
            interviews = self._readiness_rows(conn, "interviews", "created_at")
            practices = self._readiness_rows(conn, "practice_records", "created_at")
            audios = self._readiness_rows(conn, "audio_records", "created_at")
            opportunities = self._readiness_opportunities(conn)

        components = {
            "resume": self._score_resume_component(resume),
            "alignment": self._score_alignment_component(matches),
            "interview": self._score_interview_component(interviews),
            "practice": self._score_practice_component(practices, audios),
            "pipeline": self._score_pipeline_component(opportunities),
        }
        for name, weight in READINESS_WEIGHTS.items():
            components[name]["weight"] = weight

        weighted = round(
            sum(components[name]["score"] * weight for name, weight in READINESS_WEIGHTS.items())
            / 100
        )
        caps: list[str] = []
        blockers: list[str] = []
        weekly_plan: list[dict[str, str]] = []

        if resume is None:
            caps.append("no_resume")
            blockers.append("缺少可用主简历，准备度最高限制为 30。")
            weekly_plan.append({"title": "完善一份主简历并完成审计", "page": "resume", "module": "input"})
            weighted = min(weighted, 30)

        real_matches = [
            row
            for row in matches
            if self._has_real_jd(row) and self._valid_score(row.get("match_score"))
        ]
        if not real_matches:
            caps.append("no_real_jd_match")
            blockers.append("尚无基于真实 JD 的有效匹配，准备度最高限制为 55。")
            weekly_plan.append({"title": "选择真实 JD 完成一次匹配", "page": "resume", "module": "jd"})
            weighted = min(weighted, 55)

        interview_scores = self._valid_scores(interviews)
        low_interview = bool(interview_scores) and self._mean(interview_scores[:READINESS_RECENT_LIMIT]) < 40
        if low_interview:
            blockers.append("最近完成的面试平均分低于 40，先修复核心回答再投递。")
            weekly_plan.append({"title": "复盘低分面试并重练核心回答", "page": "interview", "module": "records"})

        if not interview_scores:
            blockers.append("缺少已完成且有有效评分的模拟面试。")
            weekly_plan.append({"title": "完成一轮模拟面试", "page": "interview", "module": "mock"})
        if components["practice"]["score"] < 50:
            weekly_plan.append({"title": "完成题库练习和录音复盘", "page": "interview", "module": "practice"})
        if not opportunities:
            weekly_plan.append({"title": "建立投递看板并设置下一步", "page": "tracker", "module": "add"})

        weighted = self._clamp(weighted)
        if weighted >= DELIVERABLE_THRESHOLD and not caps and not low_interview:
            label = "可投递"
        elif weighted >= POLISH_THRESHOLD:
            label = "需要打磨"
        else:
            label = "先补基础"

        funnel: dict[str, int] = {}
        for row in opportunities:
            status = str(row.get("status") or "未设置")
            funnel[status] = funnel.get(status, 0) + 1

        if not weekly_plan:
            weekly_plan = [
                {"title": "复盘最近一次低分证据", "page": "interview", "module": "records"},
                {"title": "推进一个投递阶段", "page": "tracker", "module": "board"},
                {"title": "复核主简历与目标 JD", "page": "resume", "module": "jd"},
            ]

        return {
            "score": weighted,
            "label": label,
            "components": components,
            "caps": caps,
            "blockers": blockers[:5],
            "weekly_plan": weekly_plan[:4],
            "summary": f"当前准备度 {weighted}/100，依据近期质量、完成度、时效和趋势综合计算。",
            "funnel": funnel,
        }

    def _readiness_resume(self, conn: sqlite3.Connection) -> dict[str, Any] | None:
        if not self._table_exists(conn, "resumes"):
            return None
        columns = self._table_columns(conn, "resumes")
        status_filter = "AND (status IS NULL OR status IN ('active', 'main'))" if "status" in columns else ""
        order_column = "updated_at" if "updated_at" in columns else "created_at"
        row = conn.execute(
            f"SELECT * FROM resumes WHERE user_id = ? {status_filter} "
            f"ORDER BY {order_column} DESC, id DESC LIMIT 1",
            (self.local_user_id,),
        ).fetchone()
        return dict(row) if row else None

    def _readiness_matches(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        if not self._table_exists(conn, "job_matches"):
            return []
        columns = self._table_columns(conn, "job_matches")
        jd_expression = "m.jd_text"
        join = ""
        application_filter = ""
        if "application_id" in columns and self._table_exists(conn, "job_applications"):
            application_columns = self._table_columns(conn, "job_applications")
            if "jd_text" in application_columns:
                jd_expression = "COALESCE(m.jd_text, a.jd_text)"
                deleted_filter = "AND a.deleted_at IS NULL" if "deleted_at" in application_columns else ""
                join = f"LEFT JOIN job_applications a ON a.id = m.application_id {deleted_filter}"
                if "deleted_at" in application_columns:
                    application_filter = "AND (m.application_id IS NULL OR a.id IS NOT NULL)"
        if "jd_text" not in columns:
            jd_expression = "a.jd_text" if join else "NULL"
        score_expression = "m.match_score" if "match_score" in columns else "NULL"
        analysis_expression = "m.analysis" if "analysis" in columns else "NULL"
        created_expression = "m.created_at" if "created_at" in columns else "NULL"
        rows = conn.execute(
            f"""SELECT m.id, {score_expression} AS match_score,
                       {analysis_expression} AS analysis, {jd_expression} AS jd_text,
                       {created_expression} AS created_at
                FROM job_matches m {join}
                WHERE m.user_id = ? {application_filter}
                ORDER BY {created_expression} DESC, m.id DESC LIMIT 20""",
            (self.local_user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _readiness_rows(
        self, conn: sqlite3.Connection, table: str, timestamp_column: str
    ) -> list[dict[str, Any]]:
        if not self._table_exists(conn, table):
            return []
        columns = self._table_columns(conn, table)
        if "score" not in columns:
            return []
        timestamp = timestamp_column if timestamp_column in columns else "NULL"
        rows = conn.execute(
            f"SELECT id, score, {timestamp} AS created_at FROM {table} "
            f"WHERE user_id = ? ORDER BY {timestamp} DESC, id DESC LIMIT 20",
            (self.local_user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _readiness_opportunities(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        if not self._table_exists(conn, "job_applications"):
            return []
        columns = self._table_columns(conn, "job_applications")
        deleted_filter = "AND deleted_at IS NULL" if "deleted_at" in columns else ""
        selected = [name for name in ("id", "status", "next_action_at", "updated_at") if name in columns]
        rows = conn.execute(
            f"SELECT {', '.join(selected)} FROM job_applications "
            f"WHERE user_id = ? {deleted_filter} ORDER BY id DESC LIMIT 50",
            (self.local_user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _score_resume_component(self, resume: dict[str, Any] | None) -> dict[str, Any]:
        if not resume:
            return self._component(0, [])
        content = str(resume.get("content") or "")
        completeness = min(45, len(content.strip()) // 4)
        section_terms = ("summary", "experience", "education", "skills", "项目", "经历", "教育", "技能")
        completeness += min(40, sum(10 for term in section_terms if term.lower() in content.lower()))
        if any(character.isdigit() for character in content):
            completeness += 8
        completeness = self._clamp(completeness)
        audit_score = self._extract_quality_score(resume.get("analysis_result"))
        score = round(audit_score * 0.7 + completeness * 0.3) if audit_score is not None else completeness
        score *= 0.85 + 0.15 * self._recency_factor(resume.get("updated_at") or resume.get("created_at"))
        evidence = [self._evidence("主简历质量与完整度已评估", resume.get("id"), resume.get("updated_at") or resume.get("created_at"))]
        return self._component(score, evidence)

    def _score_alignment_component(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        valid = [row for row in matches if self._has_real_jd(row) and self._valid_score(row.get("match_score"))]
        if not valid:
            return self._component(0, [])
        recent = valid[:READINESS_RECENT_LIMIT]
        scores = [float(row["match_score"]) for row in recent]
        quality = self._mean(
            [score * self._recency_factor(row.get("created_at")) for score, row in zip(scores, recent)]
        )
        confidence = min(4, max(0, len(recent) - 1)) if quality > 0 else 0
        evidence = [
            self._evidence(f"真实 JD 匹配得分 {round(float(row['match_score']))}", row.get("id"), row.get("created_at"))
            for row in recent[:3]
        ]
        return self._component(round(quality + confidence), evidence)

    def _score_interview_component(self, interviews: list[dict[str, Any]]) -> dict[str, Any]:
        valid_rows = [row for row in interviews if self._valid_score(row.get("score"))]
        if not valid_rows:
            return self._component(0, [])
        recent = valid_rows[:READINESS_RECENT_LIMIT]
        scores = [float(row["score"]) for row in recent]
        quality = self._mean(
            [score * self._recency_factor(row.get("created_at")) for score, row in zip(scores, recent)]
        )
        trend = 0.0
        if len(scores) >= 2:
            trend = max(-8.0, min(8.0, (scores[0] - scores[-1]) * 0.25))
        confidence = min(4, len(scores) - 1) if quality > 0 else 0
        evidence = [
            self._evidence(f"已完成面试得分 {round(float(row['score']))}", row.get("id"), row.get("created_at"))
            for row in recent[:3]
        ]
        return self._component(round(quality + trend + confidence), evidence)

    def _score_practice_component(
        self, practices: list[dict[str, Any]], audios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        practice_rows = [row for row in practices if self._valid_score(row.get("score"))][:READINESS_RECENT_LIMIT]
        audio_rows = [row for row in audios if self._valid_score(row.get("score"))][:READINESS_RECENT_LIMIT]
        if not practice_rows and not audio_rows:
            return self._component(0, [])
        practice_quality = self._mean(
            [float(row["score"]) * self._recency_factor(row.get("created_at")) for row in practice_rows]
        ) if practice_rows else 0
        audio_quality = self._mean(
            [float(row["score"]) * self._recency_factor(row.get("created_at")) for row in audio_rows]
        ) if audio_rows else 0
        if practice_rows and audio_rows:
            quality = practice_quality * 0.65 + audio_quality * 0.35
        else:
            quality = (practice_quality or audio_quality) * 0.75
        valid_count = len(practice_rows) + len(audio_rows)
        confidence = min(4, max(0, valid_count - 1)) if quality > 0 else 0
        evidence = [
            *[self._evidence(f"练习得分 {round(float(row['score']))}", row.get("id"), row.get("created_at")) for row in practice_rows[:2]],
            *[self._evidence(f"录音复盘得分 {round(float(row['score']))}", row.get("id"), row.get("created_at")) for row in audio_rows[:1]],
        ]
        return self._component(round(quality + confidence), evidence)

    def _score_pipeline_component(self, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        if not opportunities:
            return self._component(0, [])
        stage_indexes = []
        hygienic = 0
        recent = 0
        evidence = []
        active_max = max(1, len(_ACTIVE_PIPELINE) - 1)
        for row in opportunities:
            status = row.get("status")
            if status == "Offer":
                stage_indexes.append(100)
            elif status in _ACTIVE_PIPELINE:
                stage_indexes.append(min(APPLICATION_STATUSES.index(status), active_max) / active_max * 100)
            elif status in APPLICATION_STATUSES:
                stage_indexes.append(20)
            if self._next_action_is_hygienic(row.get("next_action_at")):
                hygienic += 1
            age = self._age_days(row.get("updated_at"))
            if age is not None and age <= 30:
                recent += 1
            if len(evidence) < 3:
                evidence.append(self._evidence(f"投递阶段：{status or '未设置'}", row.get("id"), row.get("updated_at")))
        progression = self._mean(stage_indexes) if stage_indexes else 0
        hygiene = hygienic / len(opportunities) * 100
        recency = recent / len(opportunities) * 100
        score = round(progression * 0.55 + hygiene * 0.30 + recency * 0.15)
        return self._component(score, evidence)

    @staticmethod
    def _component(score: float, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        return {"score": CareerService._clamp(score), "evidence": evidence}

    @staticmethod
    def _evidence(reason: str, entity_id: Any, timestamp: Any) -> dict[str, Any]:
        return {"reason": reason, "entity_id": entity_id, "timestamp": timestamp}

    @staticmethod
    def _extract_quality_score(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = value
        candidates: list[Any] = []
        if isinstance(parsed, dict):
            for key in ("score", "overall_score", "quality", "completeness"):
                if key in parsed:
                    candidates.append(parsed[key])
            for nested in parsed.values():
                if isinstance(nested, dict):
                    candidates.extend(nested.get(key) for key in ("score", "overall_score") if key in nested)
        elif isinstance(parsed, (int, float)):
            candidates.append(parsed)
        elif isinstance(parsed, str):
            match = re.search(r"(?:score|得分|总分)\s*[:：]?\s*(\d{1,3})", parsed, re.IGNORECASE)
            if match:
                candidates.append(int(match.group(1)))
        valid = [float(item) for item in candidates if CareerService._valid_score(item)]
        return CareerService._mean(valid) if valid else None

    @staticmethod
    def _valid_score(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100

    @classmethod
    def _valid_scores(cls, rows: list[dict[str, Any]]) -> list[float]:
        return [float(row["score"]) for row in rows if cls._valid_score(row.get("score"))]

    @staticmethod
    def _has_real_jd(row: dict[str, Any]) -> bool:
        return len(str(row.get("jd_text") or "").strip()) >= REAL_JD_MIN_LENGTH

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _clamp(value: float) -> int:
        return max(0, min(100, round(value)))

    @staticmethod
    def _age_days(value: Any) -> int | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0, (datetime.now(timezone.utc) - parsed).days)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _recency_factor(cls, value: Any) -> float:
        age = cls._age_days(value)
        if age is None:
            return 0.85
        if age <= 30:
            return 1.0
        if age <= 90:
            return 0.85
        if age <= 180:
            return 0.70
        return 0.55

    @staticmethod
    def _next_action_is_hygienic(value: Any) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (parsed - datetime.now(timezone.utc)).days >= -7
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone() is not None

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}

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

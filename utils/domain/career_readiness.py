from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from .database import APPLICATION_STATUSES

_ACTIVE_PIPELINE = APPLICATION_STATUSES[:8]

# Readiness is a deterministic local heuristic based on evidence quality,
# recency, completion and trend. Repeated records never add a count bonus.
READINESS_WEIGHTS = {
    "resume": 25,
    "alignment": 20,
    "interview": 25,
    "practice": 15,
    "pipeline": 15,
}
READINESS_RECENT_LIMIT = 5
MIN_MEANINGFUL_JD_LENGTH = 80
JD_RESPONSIBILITY_MARKERS = ("岗位职责", "工作职责", "负责", "responsibilities", "duties")
JD_REQUIREMENT_MARKERS = (
    "任职要求",
    "岗位要求",
    "要求",
    "熟悉",
    "技能",
    "requirements",
    "qualifications",
)
MIN_JD_UNIQUE_CHARACTERS = 18
DELIVERABLE_THRESHOLD = 70
POLISH_THRESHOLD = 42


def _normalize_evidence_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def is_meaningful_jd_snapshot(value: Any) -> bool:
    normalized = _normalize_evidence_text(value)
    compact = "".join(normalized.split())
    if len(normalized) < MIN_MEANINGFUL_JD_LENGTH:
        return False
    if len(set(compact)) < MIN_JD_UNIQUE_CHARACTERS:
        return False
    return any(marker in normalized for marker in JD_RESPONSIBILITY_MARKERS) and any(
        marker in normalized for marker in JD_REQUIREMENT_MARKERS
    )


class CareerReadinessMixin:
    def calculate_readiness(self, user_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        with self._unit_of_work() as unit_of_work:
            evidence = unit_of_work.career.readiness_evidence(self.local_user_id)
        resume = evidence["resume"]
        matches = evidence["matches"]
        interviews = evidence["interviews"]
        practices = evidence["practices"]
        audios = evidence["audios"]
        opportunities = evidence["opportunities"]

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
            weekly_plan.append(
                {"title": "完善一份主简历并完成审计", "page": "resume", "module": "input"}
            )
            weighted = min(weighted, 30)

        real_matches = [
            row
            for row in matches
            if self._has_real_jd(row) and self._valid_score(row.get("match_score"))
        ]
        if not real_matches:
            caps.append("no_real_jd_match")
            blockers.append("尚无基于真实 JD 的有效匹配，准备度最高限制为 55。")
            weekly_plan.append(
                {"title": "选择真实 JD 完成一次匹配", "page": "resume", "module": "jd"}
            )
            weighted = min(weighted, 55)

        interview_scores = self._valid_scores(
            self._unique_scored_rows(
                [row for row in interviews if self._valid_score(row.get("score"))],
                "interview",
            )
        )
        low_interview = (
            bool(interview_scores) and self._mean(interview_scores[:READINESS_RECENT_LIMIT]) < 40
        )
        if low_interview:
            blockers.append("最近完成的面试平均分低于 40，先修复核心回答再投递。")
            weekly_plan.append(
                {"title": "复盘低分面试并重练核心回答", "page": "interview", "module": "records"}
            )

        if not interview_scores:
            blockers.append("缺少已完成且有有效评分的模拟面试。")
            weekly_plan.append({"title": "完成一轮模拟面试", "page": "interview", "module": "mock"})
        if components["practice"]["score"] < 50:
            weekly_plan.append(
                {"title": "完成题库练习和录音复盘", "page": "interview", "module": "practice"}
            )
        if not opportunities:
            weekly_plan.append(
                {"title": "建立投递看板并设置下一步", "page": "tracker", "module": "add"}
            )

        weighted = self._clamp(weighted)
        label = self._readiness_label(weighted, caps, low_interview)

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

    def _score_resume_component(self, resume: dict[str, Any] | None) -> dict[str, Any]:
        if not resume:
            return self._component(0, [])
        content = str(resume.get("content") or "")
        completeness = min(45, len(content.strip()) // 4)
        section_terms = (
            "summary",
            "experience",
            "education",
            "skills",
            "项目",
            "经历",
            "教育",
            "技能",
        )
        completeness += min(
            40, sum(10 for term in section_terms if term.lower() in content.lower())
        )
        if any(character.isdigit() for character in content):
            completeness += 8
        completeness = self._clamp(completeness)
        audit_score = self._extract_quality_score(resume.get("analysis_result"))
        score = (
            round(audit_score * 0.7 + completeness * 0.3)
            if audit_score is not None
            else completeness
        )
        score *= 0.85 + 0.15 * self._recency_factor(
            resume.get("updated_at") or resume.get("created_at")
        )
        evidence = [
            self._evidence(
                "主简历质量与完整度已评估",
                resume.get("id"),
                resume.get("updated_at") or resume.get("created_at"),
            )
        ]
        return self._component(score, evidence)

    def _score_alignment_component(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        valid = self._unique_scored_rows(
            [
                row
                for row in matches
                if self._has_real_jd(row) and self._valid_score(row.get("match_score"))
            ],
            "match",
        )
        if not valid:
            return self._component(0, [])
        recent = valid[:READINESS_RECENT_LIMIT]
        scores = [float(row["match_score"]) for row in recent]
        quality = self._mean(
            [
                score * self._recency_factor(row.get("created_at"))
                for score, row in zip(scores, recent)
            ]
        )
        evidence = [
            self._evidence(
                f"真实 JD 匹配得分 {round(float(row['match_score']))}",
                row.get("id"),
                row.get("created_at"),
            )
            for row in recent[:3]
        ]
        return self._component(round(quality), evidence)

    def _score_interview_component(self, interviews: list[dict[str, Any]]) -> dict[str, Any]:
        valid_rows = self._unique_scored_rows(
            [row for row in interviews if self._valid_score(row.get("score"))],
            "interview",
        )
        if not valid_rows:
            return self._component(0, [])
        recent = valid_rows[:READINESS_RECENT_LIMIT]
        scores = [float(row["score"]) for row in recent]
        quality = self._mean(
            [
                score * self._recency_factor(row.get("created_at"))
                for score, row in zip(scores, recent)
            ]
        )
        trend = 0.0
        if len(scores) >= 2:
            trend = max(-8.0, min(8.0, (scores[0] - scores[-1]) * 0.25))
        evidence = [
            self._evidence(
                f"已完成面试得分 {round(float(row['score']))}", row.get("id"), row.get("created_at")
            )
            for row in recent[:3]
        ]
        return self._component(round(quality + trend), evidence)

    def _score_practice_component(
        self, practices: list[dict[str, Any]], audios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        practice_rows = self._unique_scored_rows(
            [row for row in practices if self._valid_score(row.get("score"))],
            "practice",
        )[:READINESS_RECENT_LIMIT]
        audio_rows = self._unique_scored_rows(
            [row for row in audios if self._valid_score(row.get("score"))],
            "audio",
        )[:READINESS_RECENT_LIMIT]
        if not practice_rows and not audio_rows:
            return self._component(0, [])
        practice_quality = (
            self._mean(
                [
                    float(row["score"]) * self._recency_factor(row.get("created_at"))
                    for row in practice_rows
                ]
            )
            if practice_rows
            else 0
        )
        audio_quality = (
            self._mean(
                [
                    float(row["score"]) * self._recency_factor(row.get("created_at"))
                    for row in audio_rows
                ]
            )
            if audio_rows
            else 0
        )
        if practice_rows and audio_rows:
            quality = practice_quality * 0.65 + audio_quality * 0.35
        else:
            quality = (practice_quality or audio_quality) * 0.75
        evidence = [
            *[
                self._evidence(
                    f"练习得分 {round(float(row['score']))}", row.get("id"), row.get("created_at")
                )
                for row in practice_rows[:2]
            ],
            *[
                self._evidence(
                    f"录音复盘得分 {round(float(row['score']))}",
                    row.get("id"),
                    row.get("created_at"),
                )
                for row in audio_rows[:1]
            ],
        ]
        return self._component(round(quality), evidence)

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
                stage_indexes.append(
                    min(APPLICATION_STATUSES.index(status), active_max) / active_max * 100
                )
            elif status in APPLICATION_STATUSES:
                stage_indexes.append(20)
            if self._next_action_is_hygienic(row.get("next_action_at")):
                hygienic += 1
            age = self._age_days(row.get("updated_at"))
            if age is not None and age <= 30:
                recent += 1
            if len(evidence) < 3:
                evidence.append(
                    self._evidence(
                        f"投递阶段：{status or '未设置'}", row.get("id"), row.get("updated_at")
                    )
                )
        progression = self._mean(stage_indexes) if stage_indexes else 0
        hygiene = hygienic / len(opportunities) * 100
        recency = recent / len(opportunities) * 100
        score = round(progression * 0.55 + hygiene * 0.30 + recency * 0.15)
        return self._component(score, evidence)

    @staticmethod
    def _component(score: float, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        return {"score": CareerReadinessMixin._clamp(score), "evidence": evidence}

    @staticmethod
    def _readiness_label(score: int, caps: list[str], low_interview: bool) -> str:
        if score >= DELIVERABLE_THRESHOLD and not caps and not low_interview:
            return "可投递"
        if score >= POLISH_THRESHOLD:
            return "需要打磨"
        return "先补基础"

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
                    candidates.extend(
                        nested.get(key) for key in ("score", "overall_score") if key in nested
                    )
        elif isinstance(parsed, (int, float)):
            candidates.append(parsed)
        elif isinstance(parsed, str):
            match = re.search(r"(?:score|得分|总分)\s*[:：]?\s*(\d{1,3})", parsed, re.IGNORECASE)
            if match:
                candidates.append(int(match.group(1)))
        valid = [float(item) for item in candidates if CareerReadinessMixin._valid_score(item)]
        return CareerReadinessMixin._mean(valid) if valid else None

    @staticmethod
    def _valid_score(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100

    @classmethod
    def _valid_scores(cls, rows: list[dict[str, Any]]) -> list[float]:
        return [float(row["score"]) for row in rows if cls._valid_score(row.get("score"))]

    @staticmethod
    def _unique_scored_rows(rows: list[dict[str, Any]], evidence_type: str) -> list[dict[str, Any]]:
        unique = []
        seen = set()
        for row in rows:
            key = CareerReadinessMixin._evidence_fingerprint(row, evidence_type)
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique

    @staticmethod
    def _evidence_fingerprint(row: dict[str, Any], evidence_type: str) -> str:
        if evidence_type == "match":
            identity = (
                row.get("resume_id"),
                _normalize_evidence_text(row.get("job_title")),
                f"application:{row['application_id']}"
                if row.get("application_id") is not None
                else hashlib.sha256(
                    _normalize_evidence_text(row.get("jd_text")).encode("utf-8")
                ).hexdigest(),
            )
        elif evidence_type == "interview":
            if row.get("source_session_id"):
                identity = ("session", str(row["source_session_id"]))
            else:
                identity = (
                    row.get("resume_id"),
                    _normalize_evidence_text(row.get("job_title")),
                    _normalize_evidence_text(row.get("conversation")),
                )
        elif evidence_type == "practice":
            identity = tuple(
                _normalize_evidence_text(row.get(field))
                for field in ("category", "question", "answer")
            )
        elif evidence_type == "audio":
            identity = (
                _normalize_evidence_text(row.get("transcript")),
                _normalize_evidence_text(row.get("metrics")),
                _normalize_evidence_text(row.get("audio_file")),
            )
        else:
            raise ValueError("unknown evidence type")
        return hashlib.sha256(repr(identity).encode("utf-8")).hexdigest()

    @staticmethod
    def _has_real_jd(row: dict[str, Any]) -> bool:
        return is_meaningful_jd_snapshot(row.get("jd_text"))

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _clamp(value: float) -> int:
        return max(0, min(100, round(value)))

    @staticmethod
    def _age_days(value: Any) -> int | None:
        parsed = CareerReadinessMixin._timestamp_utc(value)
        if parsed is None:
            return None
        return max(0, (datetime.now(UTC) - parsed).days)

    @staticmethod
    def _timestamp_utc(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _sort_recent_rows(
        cls, rows: list[dict[str, Any]], timestamp_field: str = "created_at"
    ) -> list[dict[str, Any]]:
        minimum = datetime.min.replace(tzinfo=UTC)
        return sorted(
            rows,
            key=lambda row: (
                cls._timestamp_utc(row.get(timestamp_field)) or minimum,
                int(row.get("id") or 0),
            ),
            reverse=True,
        )

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
                parsed = parsed.replace(tzinfo=UTC)
            return (parsed - datetime.now(UTC)).days >= -7
        except (TypeError, ValueError):
            return False

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Callable

from .database import connect


StageBuilder = Callable[[dict[str, Any]], list[tuple[str, str]]]
AnswerEvaluator = Callable[
    [dict[str, Any], str, float | None, str],
    tuple[dict[str, Any], dict[str, Any], bool],
]
ProfileResolver = Callable[[str], dict[str, str]]
ProfileSelector = Callable[[str | None, str, str], str]


def _default_stages(session: dict[str, Any]) -> list[tuple[str, str]]:
    job_title = session["job_title"]
    return [
        ("resume_deep_dive", f"请展开讲一段最能体现你适合 {job_title} 的经历。"),
        ("professional", f"请讲讲你会如何处理一项典型的 {job_title} 专业任务。"),
        ("behavioral", "讲一次你发现问题并推动解决的经历。"),
        ("candidate_questions", "现在进入反问环节，你会问哪两个问题？"),
        ("finished", "面试结束，系统已生成综合反馈。"),
    ]


def _default_evaluator(
    _session: dict[str, Any], answer: str, duration_seconds: float | None, stage: str
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    compact = "".join(answer.lower().split())
    skipped = compact in {"skip", "pass", "next", "跳过", "下一题", "不知道", "不会"}
    score = 0 if skipped else 75
    voice = {"overall_score": score, "tips": [], "duration_seconds": duration_seconds}
    feedback = {
        "score": score,
        "summary": "本题已跳过。" if skipped else f"已完成 {stage} 阶段回答。",
        "voice": voice,
        "suggestions": [],
    }
    return {"role": "candidate", "content": answer, "voice": voice}, feedback, skipped


def _default_profile(profile: str) -> dict[str, str]:
    return {"id": profile, "label": profile, "interviewer": "面试官"}


class InterviewService:
    """Persist and resume the six-step mock interview workflow."""

    def __init__(
        self,
        db_path: str | os.PathLike[str],
        local_user_id: int = 1,
        *,
        stages_builder: StageBuilder | None = None,
        answer_evaluator: AnswerEvaluator | None = None,
        profile_resolver: ProfileResolver | None = None,
        profile_selector: ProfileSelector | None = None,
        completion_summary: str | None = None,
    ):
        self.db_path = os.fspath(db_path)
        self.local_user_id = int(local_user_id)
        self.stages_builder = stages_builder or _default_stages
        self.answer_evaluator = answer_evaluator or _default_evaluator
        self.profile_resolver = profile_resolver or _default_profile
        self.profile_selector = profile_selector or (lambda profile, _resume, _job: profile or "tech")
        self.completion_summary = completion_summary or (
            "整体流程完成。建议把自我介绍压缩到 120 秒内，并准备 2 个项目深挖版本、"
            "1 个问题定位案例和 1 个团队协作案例。"
        )

    def start(
        self,
        user_id: int,
        resume_id: int | None,
        job_title: str,
        jd: str,
        mode: str,
        career_profile: str | None,
        application_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        resume_id = self._optional_id(resume_id, "resume_id")
        application_id = self._optional_id(application_id, "application_id")
        job_title = self._text(job_title, "job_title", 300, required=True)
        jd = self._text(jd, "jd", 200_000) or ""
        mode = self._text(mode, "mode", 100) or "standard"
        requested_profile = self._text(career_profile, "career_profile", 100)

        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            resume_content = ""
            if resume_id is not None:
                resume = self._owned_resource(conn, "resumes", resume_id, "resume")
                if "status" in resume.keys() and resume["status"] == "archived":
                    raise LookupError("resume not found")
                resume_content = resume["content"] or ""
            if application_id is not None:
                opportunity = self._owned_resource(
                    conn, "job_applications", application_id, "opportunity"
                )
                if "deleted_at" in opportunity.keys() and opportunity["deleted_at"]:
                    raise LookupError("opportunity not found")

            profile_key = self.profile_selector(requested_profile, resume_content, job_title)
            profile_key = self._text(profile_key, "career_profile", 100, required=True)
            profile = self.profile_resolver(profile_key)
            if not isinstance(profile, dict):
                raise ValueError("profile resolver must return an object")
            profile = {
                "id": str(profile.get("id") or profile_key),
                "label": str(profile.get("label") or profile_key),
                "interviewer": str(profile.get("interviewer") or "面试官"),
            }
            question = (
                f"欢迎参加{profile['interviewer']}模拟面试。请先做一个 2 分钟自我介绍，"
                "重点说清楚目标岗位、相关经历和你的优势。"
            )
            state = {
                "version": 1,
                "jd": jd,
                "career_profile": profile_key,
                "profile": profile,
                "resume_content": resume_content,
                "stage_index": 0,
                "conversation": [
                    {"role": "interviewer", "stage": "opening", "content": question}
                ],
                "current_question": question,
                "last_feedback": None,
            }
            cursor = conn.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, application_id, resume_id, job_title, mode, status,
                    current_stage, conversation_json
                ) VALUES (?, ?, ?, ?, ?, 'active', 'opening', ?)
                """,
                (
                    self.local_user_id,
                    application_id,
                    resume_id,
                    job_title,
                    mode,
                    self._dump(state),
                ),
            )
            session_id = cursor.lastrowid
            self._write_event(
                conn,
                session_id,
                "interview.started",
                {"resume_id": resume_id, "application_id": application_id, "mode": mode},
            )
            row = conn.execute(
                "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return self._response(row, state)

    def get(self, user_id: int, session_id: int) -> dict[str, Any] | None:
        self._require_local_user(user_id)
        session_id = self._required_id(session_id, "session_id")
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        self._require_row_owner(row)
        return self._response(row, self._load_state(row))

    def answer(
        self,
        user_id: int,
        session_id: int,
        answer: str,
        duration_seconds: float | None = None,
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        session_id = self._required_id(session_id, "session_id")
        answer = self._text(answer, "answer", 200_000, required=True)
        duration_seconds = self._duration(duration_seconds)

        with connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                raise LookupError("interview session not found")
            self._require_row_owner(row)
            state = self._load_state(row)
            if row["status"] == "completed":
                response = self._response(row, state)
                response["idempotent"] = True
                return response

            stages = self.stages_builder(self._session_context(row, state))
            if not isinstance(stages, list) or len(stages) != 5:
                raise ValueError("interview flow must contain five post-opening stages")
            stage_index = int(state.get("stage_index", 0)) + 1
            stage, question = stages[min(stage_index - 1, len(stages) - 1)]
            candidate, feedback, skipped = self.answer_evaluator(
                self._session_context(row, state), answer, duration_seconds, stage
            )
            if not isinstance(candidate, dict) or not isinstance(feedback, dict):
                raise ValueError("answer evaluator returned invalid data")
            state["conversation"].append(candidate)
            state["stage_index"] = stage_index
            state["current_question"] = question
            state["last_feedback"] = feedback

            completed = stage == "finished"
            score = None
            if completed:
                candidates = [
                    item
                    for item in state["conversation"]
                    if isinstance(item, dict) and item.get("role") == "candidate"
                ]
                score = int(
                    sum(item.get("voice", {}).get("overall_score", 75) for item in candidates)
                    / max(1, len(candidates))
                )
                feedback["score"] = score
                feedback["summary"] = self.completion_summary
            else:
                state["conversation"].append(
                    {"role": "interviewer", "stage": stage, "content": question}
                )

            conn.execute(
                """
                UPDATE interview_sessions
                SET status = ?, current_stage = ?, conversation_json = ?, score = ?,
                    feedback = ?, completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE completed_at END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (
                    "completed" if completed else "active",
                    stage,
                    self._dump(state),
                    score,
                    self._dump(feedback),
                    completed,
                    session_id,
                    self.local_user_id,
                ),
            )
            self._write_event(
                conn,
                session_id,
                "interview.answered",
                {
                    "stage": stage,
                    "stage_index": stage_index,
                    "skipped": bool(skipped),
                    "has_duration": duration_seconds is not None,
                },
            )
            if completed:
                conn.execute(
                    """
                    INSERT INTO interviews (
                        user_id, resume_id, job_title, conversation, score, feedback
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.local_user_id,
                        row["resume_id"],
                        row["job_title"],
                        self._dump(state["conversation"]),
                        score,
                        self._dump(feedback),
                    ),
                )
                self._write_event(
                    conn,
                    session_id,
                    "interview.completed",
                    {"score": score, "answer_count": len(candidates)},
                )
            row = conn.execute(
                "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return self._response(row, state)

    def list_open(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM interview_sessions
                WHERE user_id = ? AND status != 'completed'
                ORDER BY updated_at DESC, id DESC
                """,
                (self.local_user_id,),
            ).fetchall()
        return [self._response(row, self._load_state(row)) for row in rows]

    def _response(self, row: sqlite3.Row, state: dict[str, Any]) -> dict[str, Any]:
        conversation = state.get("conversation")
        if not isinstance(conversation, list):
            raise ValueError("invalid interview session state")
        question = str(state.get("current_question") or "")
        if not question:
            for item in reversed(conversation):
                if isinstance(item, dict) and item.get("role") == "interviewer":
                    question = str(item.get("content") or "")
                    break
        result = {
            "success": True,
            "session_id": row["id"],
            "stage": row["current_stage"],
            "question": question,
            "profile": state.get("profile") or {},
            "progress": min(int(state.get("stage_index", 0)) + 1, 6),
            "total": 6,
            "status": row["status"],
            "job_title": row["job_title"],
            "mode": row["mode"],
            "resume_id": row["resume_id"],
            "application_id": row["application_id"],
        }
        if state.get("last_feedback") is not None:
            result["feedback"] = state["last_feedback"]
        return result

    def _session_context(self, row: sqlite3.Row, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": row["id"],
            "user_id": row["user_id"],
            "resume_id": row["resume_id"],
            "application_id": row["application_id"],
            "job_title": row["job_title"],
            "mode": row["mode"],
            **state,
        }

    def _owned_resource(
        self, conn: sqlite3.Connection, table: str, row_id: int, label: str
    ) -> sqlite3.Row:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        if not row:
            raise LookupError(f"{label} not found")
        if row["user_id"] != self.local_user_id:
            raise PermissionError(f"{label} belongs to another user")
        return row

    def _load_state(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            state = json.loads(row["conversation_json"] or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid interview session state") from exc
        if not isinstance(state, dict) or not isinstance(state.get("conversation"), list):
            raise ValueError("invalid interview session state")
        return state

    def _require_local_user(self, user_id: int) -> None:
        if user_id != self.local_user_id:
            raise PermissionError("operation is restricted to the local user")

    def _require_row_owner(self, row: sqlite3.Row) -> None:
        if row["user_id"] != self.local_user_id:
            raise PermissionError("interview session belongs to another user")

    def _write_event(
        self,
        conn: sqlite3.Connection,
        session_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO domain_events (
                user_id, aggregate_type, aggregate_id, event_type, payload_json
            ) VALUES (?, 'interview_session', ?, ?, ?)
            """,
            (
                self.local_user_id,
                str(session_id),
                event_type,
                self._dump(payload),
            ),
        )

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

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

    @classmethod
    def _required_id(cls, value: Any, name: str) -> int:
        result = cls._optional_id(value, name)
        if result is None:
            raise ValueError(f"{name} is required")
        return result

    @staticmethod
    def _optional_id(value: Any, name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if result <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return result

    @staticmethod
    def _duration(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("duration_seconds must be a number")
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("duration_seconds must be a number") from exc
        if result < 0:
            raise ValueError("duration_seconds must not be negative")
        return result


__all__ = ["InterviewService"]

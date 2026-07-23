from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

StageBuilder = Callable[[dict[str, Any]], list[tuple[str, str]]]
AnswerEvaluator = Callable[
    [dict[str, Any], str, float | None, str],
    tuple[dict[str, Any], dict[str, Any], bool],
]
ProfileResolver = Callable[[str], dict[str, str]]
ProfileSelector = Callable[[str | None, str, str], str]


class InterviewConflictError(Exception):
    """A different submission was based on an out-of-date interview stage."""


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
        db_path: str | os.PathLike[str] | None = None,
        local_user_id: int = 1,
        *,
        session_factory: Callable[[], Any] | None = None,
        repository_factory: Callable[[Any], Any] | None = None,
        stages_builder: StageBuilder | None = None,
        answer_evaluator: AnswerEvaluator | None = None,
        profile_resolver: ProfileResolver | None = None,
        profile_selector: ProfileSelector | None = None,
        completion_summary: str | None = None,
    ):
        self._database = None
        legacy_sqlite = session_factory is None
        if session_factory is None:
            if db_path is None:
                raise ValueError("db_path or session_factory is required")
            from backend.core.database import Database, sqlite_database_url

            self._database = Database(sqlite_database_url(db_path))
            session_factory = self._database.session_factory
        if repository_factory is None:
            if legacy_sqlite:
                from backend.adapters.persistence.legacy_interview_repository import (
                    LegacySqliteInterviewRepository,
                )

                repository_factory = LegacySqliteInterviewRepository
            else:
                from backend.adapters.persistence.sqlalchemy.interview_repository import (
                    SqlAlchemyInterviewRepository,
                )

                repository_factory = SqlAlchemyInterviewRepository
        self.db_path = os.fspath(db_path) if db_path is not None else None
        self.session_factory = session_factory
        self.repository_factory = repository_factory
        self.local_user_id = int(local_user_id)
        self.stages_builder = stages_builder or _default_stages
        self.answer_evaluator = answer_evaluator or _default_evaluator
        self.profile_resolver = profile_resolver or _default_profile
        self.profile_selector = profile_selector or (
            lambda profile, _resume, _job: profile or "tech"
        )
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
        action_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_local_user(user_id)
        resume_id = self._optional_id(resume_id, "resume_id")
        application_id = self._optional_id(application_id, "application_id")
        action_id = self._optional_id(action_id, "action_id")
        job_title = self._text(job_title, "job_title", 300, required=True)
        jd = self._text(jd, "jd", 200_000) or ""
        mode = self._text(mode, "mode", 100) or "standard"
        requested_profile = self._text(career_profile, "career_profile", 100)

        with self._repository(write=True) as repository:
            resume_content = ""
            if resume_id is not None:
                resume = self._owned_resource(
                    repository.get_resume(resume_id),
                    "resume",
                )
                if resume.get("status") == "archived":
                    raise LookupError("resume not found")
                resume_content = resume["content"] or ""
            if application_id is not None:
                opportunity = self._owned_resource(
                    repository.get_opportunity(application_id),
                    "opportunity",
                )
                if opportunity.get("deleted_at"):
                    raise LookupError("opportunity not found")
            if action_id is not None:
                if application_id is None:
                    raise ValueError("interview action requires an opportunity")
                action = self._owned_resource(
                    repository.get_action(action_id),
                    "action item",
                )
                if action["status"] not in {"pending", "in_progress"}:
                    raise ValueError("interview action item is not active")
                if action["action_type"] not in {"interview", "interview_plan", "mock_interview"}:
                    raise ValueError("action item is not an interview action")
                if action["application_id"] != application_id:
                    raise ValueError("interview action item opportunity does not match")

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
                "conversation": [{"role": "interviewer", "stage": "opening", "content": question}],
                "current_question": question,
                "last_feedback": None,
                "processed_submissions": {},
                "action_id": action_id,
            }
            session_id = repository.create_session(
                {
                    "user_id": self.local_user_id,
                    "application_id": application_id,
                    "resume_id": resume_id,
                    "job_title": job_title,
                    "mode": mode,
                    "status": "active",
                    "current_stage": "opening",
                    "conversation_json": self._dump(state),
                }
            )
            self._write_event(
                repository,
                session_id,
                "interview.started",
                {
                    "resume_id": resume_id,
                    "application_id": application_id,
                    "mode": mode,
                    "action_id": action_id,
                },
            )
            row = repository.get_session(session_id)
        return self._response(row, state)

    def get(self, user_id: int, session_id: int) -> dict[str, Any] | None:
        self._require_local_user(user_id)
        session_id = self._required_id(session_id, "session_id")
        with self._repository() as repository:
            row = repository.get_session(session_id)
        if not row:
            return None
        self._require_row_owner(row)
        try:
            return self._response(row, self._load_state(row))
        except ValueError:
            return self._recovery_response(row)

    def answer(
        self,
        user_id: int,
        session_id: int,
        answer: str,
        duration_seconds: float | None = None,
        *,
        submission_id: str | None = None,
        expected_stage_index: int | None = None,
    ) -> dict[str, Any]:
        """Save one answer.

        Legacy callers may omit submission metadata and retain the original at-most-once
        request behavior. Product API callers provide both fields for retry safety.
        """
        self._require_local_user(user_id)
        session_id = self._required_id(session_id, "session_id")
        answer = self._text(answer, "answer", 200_000, required=True)
        duration_seconds = self._duration(duration_seconds)
        has_submission_id = submission_id is not None
        has_expected_stage = expected_stage_index is not None
        if has_submission_id != has_expected_stage:
            raise ValueError("submission_id and expected_stage_index must be provided together")
        submission_id = self._text(submission_id, "submission_id", 128, required=has_submission_id)
        expected_stage_index = self._expected_stage_index(expected_stage_index)

        with self._repository(write=True) as repository:
            row = repository.get_session(session_id, for_update=True)
            if not row:
                raise LookupError("interview session not found")
            self._require_row_owner(row)
            state = self._load_state(row)
            processed_submissions = state.setdefault("processed_submissions", {})
            if submission_id and submission_id in processed_submissions:
                response = dict(processed_submissions[submission_id])
                response["idempotent"] = True
                return response
            current_stage_index = state["stage_index"]
            if expected_stage_index is not None and expected_stage_index != current_stage_index:
                raise InterviewConflictError(
                    "interview session stage changed; refresh before retrying"
                )
            if row["status"] == "completed":
                response = self._response(row, state)
                response["idempotent"] = True
                return response

            stages = self.stages_builder(self._session_context(row, state))
            if not isinstance(stages, list) or len(stages) != 5:
                raise ValueError("interview flow must contain five post-opening stages")
            stage_index = current_stage_index + 1
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

            repository.update_session(
                session_id,
                self.local_user_id,
                status="completed" if completed else "active",
                current_stage=stage,
                conversation_json=self._dump(state),
                score=score,
                feedback=self._dump(feedback),
                completed=completed,
            )
            self._write_event(
                repository,
                session_id,
                "interview.answered",
                {
                    "stage": stage,
                    "stage_index": stage_index,
                    "skipped": bool(skipped),
                    "has_duration": duration_seconds is not None,
                    "submission_id": submission_id,
                },
            )
            if completed:
                repository.add_completed_interview(
                    user_id=self.local_user_id,
                    resume_id=row["resume_id"],
                    job_title=row["job_title"],
                    conversation=self._dump(state["conversation"]),
                    score=score,
                    feedback=self._dump(feedback),
                    source_session_id=session_id,
                )
                self._write_event(
                    repository,
                    session_id,
                    "interview.completed",
                    {
                        "score": score,
                        "answer_count": len(candidates),
                        "action_id": state.get("action_id"),
                    },
                )
            row = repository.get_session(session_id)
            response = self._response(row, state)
            if submission_id:
                processed_submissions[submission_id] = response
                repository.update_state(
                    session_id,
                    self.local_user_id,
                    self._dump(state),
                )
        return response

    def list_open(self, user_id: int) -> list[dict[str, Any]]:
        self._require_local_user(user_id)
        with self._repository() as repository:
            rows = repository.list_open(self.local_user_id)
        sessions = []
        for row in rows:
            try:
                sessions.append(self._response(row, self._load_state(row)))
            except ValueError:
                sessions.append(self._recovery_response(row))
        return sessions

    def training_insights(self, user_id: int, limit: int = 5) -> dict[str, Any]:
        """Return bounded quality metrics without answers, transcripts, or feedback."""
        self._require_local_user(user_id)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer between 1 and 20")
        with self._repository() as repository:
            interviews = repository.recent_training_rows(
                "interview",
                self.local_user_id,
                limit,
            )
            practices = repository.recent_training_rows(
                "practice",
                self.local_user_id,
                limit,
            )
            audios = repository.recent_training_rows(
                "audio",
                self.local_user_id,
                limit,
            )

        interview_scores = [
            score
            for row in interviews
            if (score := self._quality_score(row, "interview")) is not None
        ]
        practice_scores = [
            score
            for row in practices
            if (score := self._quality_score(row, "practice")) is not None
        ]
        audio_scores = [
            score for row in audios if (score := self._quality_score(row, "audio")) is not None
        ]
        return {
            "interviews": self._quality_summary(interviews, interview_scores, "average_score"),
            "practice": self._quality_summary(practices, practice_scores, "average_score"),
            "audio": self._quality_summary(audios, audio_scores, "average_quality_score"),
        }

    @classmethod
    def _quality_score(cls, row: dict[str, Any], kind: str) -> float | None:
        direct = cls._bounded_score(row.get("score"))
        if direct is not None:
            return direct
        if kind == "practice":
            correct, total = row.get("correct_count"), row.get("total_count")
            if isinstance(correct, (int, float)) and isinstance(total, (int, float)) and total > 0:
                return cls._bounded_score(correct * 100 / total)
        if kind == "audio":
            raw = row.get("analysis_result")
            try:
                payload = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                for key in ("overall_score", "quality_score", "score"):
                    score = cls._bounded_score(payload.get(key))
                    if score is not None:
                        return score
                voice = payload.get("voice")
                if isinstance(voice, dict):
                    return cls._bounded_score(voice.get("overall_score"))
        return None

    @staticmethod
    def _bounded_score(value: Any) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return round(float(value), 1) if 0 <= value <= 100 else None

    @staticmethod
    def _quality_summary(
        rows: list[dict[str, Any]], scores: list[float], average_key: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "completed_count": len(rows),
            "scored_count": len(scores),
            average_key: round(sum(scores) / len(scores), 1) if scores else None,
        }
        timestamps = [str(row.get("created_at")) for row in rows if row.get("created_at")]
        result["latest_completed_at"] = timestamps[0] if timestamps else None
        return result

    def _response(self, row: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
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
            "session_id": str(row["id"]),
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

    @staticmethod
    def _recovery_response(row: dict[str, Any]) -> dict[str, str]:
        return {
            "session_id": str(row["id"]),
            "status": "recovery_error",
            "recovery_error": "invalid interview session state",
        }

    def _session_context(
        self,
        row: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
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
        self,
        row: dict[str, Any] | None,
        label: str,
    ) -> dict[str, Any]:
        if not row:
            raise LookupError(f"{label} not found")
        if row["user_id"] != self.local_user_id:
            raise PermissionError(f"{label} belongs to another user")
        return row

    def _load_state(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            state = json.loads(row["conversation_json"] or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid interview session state") from exc
        if not isinstance(state, dict) or not isinstance(state.get("conversation"), list):
            raise ValueError("invalid interview session state")
        version = state.get("version")
        stage_index = state.get("stage_index")
        if version != 1 or isinstance(stage_index, bool) or not isinstance(stage_index, int):
            raise ValueError("invalid interview session state")
        if not 0 <= stage_index <= 5:
            raise ValueError("invalid interview session state")
        processed = state.setdefault("processed_submissions", {})
        if not isinstance(processed, dict) or not all(
            isinstance(key, str) and isinstance(value, dict) for key, value in processed.items()
        ):
            raise ValueError("invalid interview session state")
        try:
            stages = self.stages_builder(self._session_context(row, state))
            expected_stage = "opening" if stage_index == 0 else stages[stage_index - 1][0]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid interview session state") from exc
        if len(stages) != 5 or row["current_stage"] != expected_stage:
            raise ValueError("invalid interview session state")
        if (row["status"] == "completed") != (stage_index == 5):
            raise ValueError("invalid interview session state")
        if not all(
            self._valid_cached_response(row, response, stages) for response in processed.values()
        ):
            raise ValueError("invalid interview session state")
        return state

    @staticmethod
    def _valid_cached_response(
        row: dict[str, Any],
        response: dict[str, Any],
        stages: list[tuple[str, str]],
    ) -> bool:
        progress = response.get("progress")
        if isinstance(progress, bool) or not isinstance(progress, int) or not 1 <= progress <= 6:
            return False
        expected_stage = "opening" if progress == 1 else stages[progress - 2][0]
        return (
            response.get("success") is True
            and response.get("session_id") == str(row["id"])
            and response.get("stage") == expected_stage
            and isinstance(response.get("question"), str)
            and isinstance(response.get("profile"), dict)
            and response.get("total") == 6
            and response.get("status") in {"active", "completed"}
            and response.get("job_title") == row["job_title"]
            and (response.get("mode") is None or isinstance(response.get("mode"), str))
            and isinstance(response.get("feedback"), dict)
        )

    def _require_local_user(self, user_id: int) -> None:
        if user_id != self.local_user_id:
            raise PermissionError("operation is restricted to the local user")

    def _require_row_owner(self, row: dict[str, Any]) -> None:
        if row["user_id"] != self.local_user_id:
            raise PermissionError("interview session belongs to another user")

    def _write_event(
        self,
        repository_or_connection: Any,
        session_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        method = getattr(repository_or_connection, "record_event", None)
        if callable(method):
            method(
                self.local_user_id,
                "interview_session",
                session_id,
                event_type,
                payload,
            )
            return

        from backend.adapters.persistence.legacy_event_repository import (
            LegacySqliteEventRepository,
        )

        LegacySqliteEventRepository(repository_or_connection).record_and_apply(
            self.local_user_id,
            "interview_session",
            session_id,
            event_type,
            payload,
        )

    @contextmanager
    def _repository(self, *, write: bool = False) -> Iterator[Any]:
        session = self.session_factory()
        repository = self.repository_factory(session)
        try:
            begin_write = getattr(repository, "begin_write", None)
            if write and callable(begin_write):
                begin_write()
            yield repository
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            if self._database is not None:
                self._database.dispose()

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

    @staticmethod
    def _expected_stage_index(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("expected_stage_index must be an integer")
        if not 0 <= value <= 5:
            raise ValueError("expected_stage_index must be between 0 and 5")
        return value


__all__ = ["InterviewConflictError", "InterviewService"]

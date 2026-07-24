from __future__ import annotations

from typing import Any

from utils.domain import InterviewService


class InterviewModule:
    """Deep application module for the persisted interview lifecycle."""

    def __init__(self, service: InterviewService, *, local_user_id: int):
        self._service = service
        self._local_user_id = int(local_user_id)

    def start(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._service.start(
            self._local_user_id,
            body.get("resume_id"),
            body.get("job_title", "目标岗位"),
            body.get("jd", ""),
            body.get("mode", "standard"),
            body.get("career_profile") or body.get("profile"),
            body.get("application_id"),
            body.get("action_id"),
        )

    def list_open(self) -> dict[str, Any]:
        return {
            "success": True,
            "data": self._service.list_open(self._local_user_id),
        }

    def get(self, session_id: int | str) -> tuple[dict[str, Any], int]:
        session = self._service.get(self._local_user_id, session_id)
        if session is None:
            return {
                "success": False,
                "message": "interview session not found",
                "code": "interview_session_not_found",
            }, 404
        if session.get("status") == "recovery_error":
            return {
                **session,
                "success": False,
                "message": session["recovery_error"],
                "code": "interview_session_recovery_error",
            }, 409
        return session, 200

    def answer(
        self,
        session_id: int | str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        return self._service.answer(
            self._local_user_id,
            session_id,
            body.get("answer"),
            body.get("duration_seconds"),
            submission_id=body.get("submission_id"),
            expected_stage_index=body.get("expected_stage_index"),
        )

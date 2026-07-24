from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.interviews import InterviewModule
from utils.domain import InterviewConflictError


def create_interview_router(
    module_provider: Callable[[], InterviewModule],
) -> APIRouter:
    router = APIRouter(prefix="/api/interview", tags=["interviews"])

    @router.post("/sessions")
    async def start_session(request: Request):
        try:
            body = await json_object_body(request)
            return await run_in_threadpool(module_provider().start, body)
        except (
            InterviewConflictError,
            PermissionError,
            LookupError,
            ValueError,
        ) as exc:
            return domain_error_response(exc)

    @router.get("/sessions/open")
    def list_open_sessions():
        try:
            return module_provider().list_open()
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/sessions/{session_id}")
    def get_session(session_id: str):
        try:
            payload, status_code = module_provider().get(session_id)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return JSONResponse(payload, status_code=status_code)

    @router.post("/sessions/{session_id}/answer")
    async def answer_session(session_id: str, request: Request):
        try:
            body = await json_object_body(request)
            return await run_in_threadpool(
                module_provider().answer,
                session_id,
                body,
            )
        except (
            InterviewConflictError,
            PermissionError,
            LookupError,
            ValueError,
        ) as exc:
            return domain_error_response(exc)

    return router

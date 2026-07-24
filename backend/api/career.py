from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.career import CareerModule


def create_career_router(
    module_provider: Callable[[], CareerModule],
) -> APIRouter:
    router = APIRouter(tags=["career"])

    async def body(request: Request) -> dict[str, Any]:
        return await json_object_body(request)

    async def call(method: str, *args: Any):
        try:
            return await run_in_threadpool(getattr(module_provider(), method), *args)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    async def body_call(method: str, request: Request, *args: Any):
        try:
            payload = await body(request)
        except ValueError as exc:
            return domain_error_response(exc)
        return await call(method, *args, payload)

    async def result_call(method: str, result_id: int):
        try:
            return await call(method, result_id)
        except SQLAlchemyError:
            return JSONResponse(
                {"success": False, "message": "结果暂时无法读取"},
                status_code=500,
            )

    @router.get("/api/profile")
    async def profile():
        return await call("profile")

    @router.put("/api/profile")
    async def update_profile(request: Request):
        return await body_call("update_profile", request)

    @router.get("/api/profile/{profile_id}")
    async def profile_result(profile_id: int):
        return await result_call("profile_result", profile_id)

    @router.get("/api/career-reports/{report_id}")
    async def report_result(report_id: int):
        return await result_call("report_result", report_id)

    @router.get("/api/action-items")
    async def action_items():
        return await call("action_items")

    @router.post("/api/action-items")
    async def create_action_item(request: Request):
        result = await call("create_action_item", await body(request))
        if isinstance(result, JSONResponse):
            return result
        payload, status_code = result
        return JSONResponse(payload, status_code=status_code)

    @router.post("/api/action-items/{action_id}/complete")
    async def complete_action_item(action_id: int, request: Request):
        return await body_call("complete_action_item", request, action_id)

    @router.post("/api/applications")
    async def create_application(request: Request):
        result = await body_call("create_application", request)
        if isinstance(result, JSONResponse):
            return result
        payload, status_code = result
        return JSONResponse(payload, status_code=status_code)

    @router.get("/api/applications/detail/{application_id}")
    async def application(application_id: int):
        return await call("application", application_id)

    @router.get("/api/applications/{user_id}")
    async def applications(user_id: int):
        return await call("applications", user_id)

    @router.put("/api/applications/{application_id}")
    async def update_application(application_id: int, request: Request):
        return await body_call("update_application", request, application_id)

    @router.delete("/api/applications/{application_id}")
    async def delete_application(application_id: int):
        return await call("delete_application", application_id)

    @router.post("/api/applications/{application_id}/advance")
    async def advance_application(application_id: int):
        return await call("advance_application", application_id)

    @router.post("/api/salary/evaluate")
    async def salary(request: Request):
        return await body_call("salary", request)

    return router

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response
from backend.application.career_insights import CareerInsightsModule


def create_career_insights_router(
    module_provider: Callable[[], CareerInsightsModule],
) -> APIRouter:
    router = APIRouter(tags=["career-insights"])

    async def call(method: str, *args):
        try:
            return await run_in_threadpool(getattr(module_provider(), method), *args)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/api/dashboard/{user_id}")
    async def dashboard(user_id: int):
        return await call("dashboard", user_id)

    @router.post("/api/career/report/{user_id}")
    async def report(user_id: int):
        return await call("report", user_id)

    @router.post("/api/applications/{application_id}/coach")
    async def coach(application_id: int):
        return await call("coach", application_id)

    return router

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.opportunities import OpportunityModule


def create_opportunity_router(
    module_provider: Callable[[], OpportunityModule],
) -> APIRouter:
    router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

    @router.get("")
    def list_opportunities():
        try:
            return module_provider().list()
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.post("")
    async def create_opportunity(request: Request):
        try:
            body = await json_object_body(request)
            payload, status_code = await run_in_threadpool(
                module_provider().create,
                body,
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return JSONResponse(payload, status_code=status_code)

    @router.get("/{opportunity_id}")
    def get_opportunity(opportunity_id: int):
        try:
            return module_provider().get(opportunity_id)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.put("/{opportunity_id}")
    async def update_opportunity(opportunity_id: int, request: Request):
        try:
            body = await json_object_body(request)
            return await run_in_threadpool(
                module_provider().update,
                opportunity_id,
                body,
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/{opportunity_id}/timeline")
    def opportunity_timeline(opportunity_id: int):
        try:
            return module_provider().timeline(opportunity_id)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/{opportunity_id}/workspace")
    def opportunity_workspace(opportunity_id: int):
        try:
            return module_provider().workspace(opportunity_id)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    return router

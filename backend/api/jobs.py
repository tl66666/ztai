from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.jobs import JobService


def create_jobs_router(
    module_provider: Callable[[], JobService],
) -> APIRouter:
    router = APIRouter(prefix="/api/jobs", tags=["background-jobs"])

    @router.post("/resume-analysis", status_code=202)
    async def submit_resume_analysis(
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ):
        body = await json_object_body(request)
        try:
            resume_id = int(body.pop("resume_id"))
            payload = await run_in_threadpool(
                module_provider().submit_resume_analysis,
                resume_id,
                body,
                owner_id=request.state.principal.user_id,
                idempotency_key=idempotency_key,
            )
        except (KeyError, TypeError, PermissionError, ValueError) as exc:
            return domain_error_response(exc)
        return JSONResponse(payload, status_code=202)

    @router.post("/document-conversion", status_code=202)
    async def submit_document_conversion(
        request: Request,
        file: Annotated[UploadFile, File()],
        target_format: Annotated[str, Form()],
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ):
        try:
            payload = await run_in_threadpool(
                module_provider().submit_document_conversion,
                file.file,
                filename=file.filename or "",
                target_format=target_format,
                owner_id=request.state.principal.user_id,
                idempotency_key=idempotency_key,
            )
        except (PermissionError, ValueError) as exc:
            return domain_error_response(exc)
        return JSONResponse(payload, status_code=202)

    @router.get("/{job_id}")
    async def job_status(job_id: str, request: Request):
        payload, status_code = await run_in_threadpool(
            module_provider().status,
            job_id,
            owner_id=request.state.principal.user_id,
        )
        return JSONResponse(payload, status_code=status_code)

    @router.delete("/{job_id}")
    async def cancel_job(job_id: str, request: Request):
        payload, status_code = await run_in_threadpool(
            module_provider().cancel,
            job_id,
            owner_id=request.state.principal.user_id,
        )
        return JSONResponse(payload, status_code=status_code)

    @router.get("/{job_id}/result")
    async def job_result(job_id: str, request: Request):
        try:
            result = await run_in_threadpool(
                module_provider().result,
                job_id,
                owner_id=request.state.principal.user_id,
            )
        except RuntimeError as exc:
            return JSONResponse(
                {"success": False, "message": str(exc)},
                status_code=409,
            )
        except (LookupError, PermissionError, ValueError) as exc:
            return domain_error_response(exc)
        encoded_name = quote(result.filename, safe="")
        return Response(
            result.content,
            media_type=result.media_type,
            headers={
                "Content-Disposition": (
                    f"attachment; filename*=UTF-8''{encoded_name}"
                )
            },
        )

    return router

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile

from backend.api.http import domain_error_response, json_object_body
from backend.application.resumes import ResumeModule


class ResumeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: int | None = None
    title: str
    content: str


class ResumeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    content: str


def _validation_error_response(exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        {"success": False, "message": "标题和内容不能为空。"},
        status_code=400,
    )


def create_resume_router(
    module_provider: Callable[[], ResumeModule],
) -> APIRouter:
    router = APIRouter(prefix="/api/resumes", tags=["resumes"])

    @router.post("")
    async def create_resume(request: Request):
        try:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("multipart/form-data"):
                form = await request.form()
                upload = form.get("file")
                if not isinstance(upload, StarletteUploadFile):
                    raise ValueError(
                        "请上传 PDF、Word、TXT 或图片格式简历。"
                    )
                return await _create_upload(
                    module_provider(),
                    upload,
                    title=str(form.get("title") or ""),
                    requested_user_id=form.get("user_id"),
                )
            body = ResumeCreateRequest.model_validate(
                await json_object_body(request)
            )
            payload, status_code = await run_in_threadpool(
                module_provider().create_text,
                body.model_dump(),
            )
            return JSONResponse(payload, status_code=status_code)
        except ValidationError as exc:
            return _validation_error_response(exc)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.post("/upload")
    async def upload_resume(
        file: Annotated[UploadFile, File()],
        title: Annotated[str | None, Form()] = None,
        user_id: Annotated[int | None, Form()] = None,
    ):
        try:
            return await _create_upload(
                module_provider(),
                file,
                title=title,
                requested_user_id=user_id,
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/detail/{resume_id}")
    async def resume_detail(resume_id: int):
        payload, status_code = await run_in_threadpool(
            module_provider().detail,
            resume_id,
        )
        return JSONResponse(payload, status_code=status_code)

    @router.get("/{resume_id}/original")
    async def resume_original(resume_id: int):
        try:
            original = await run_in_threadpool(
                module_provider().original,
                resume_id,
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return Response(
            original.content,
            media_type=original.media_type,
            headers={
                "Content-Disposition": (
                    "attachment; filename*=UTF-8''"
                    f"{quote(original.filename, safe='')}"
                )
            },
        )

    @router.post("/{resume_id}/replace-file")
    async def replace_resume_file(
        resume_id: int,
        file: Annotated[UploadFile, File()],
    ):
        try:
            return await run_in_threadpool(
                module_provider().replace_upload,
                resume_id,
                file.file,
                filename=file.filename or "",
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.get("/{resume_id}/export/{format_type}", response_class=FileResponse)
    async def export_resume(resume_id: int, format_type: str):
        try:
            exported = await run_in_threadpool(
                module_provider().export,
                resume_id,
                format_type,
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return FileResponse(
            exported.path,
            filename=exported.filename,
            media_type=exported.media_type,
        )

    @router.put("/{resume_id}")
    async def update_resume(resume_id: int, body: ResumeUpdateRequest):
        try:
            payload, status_code = await run_in_threadpool(
                module_provider().update,
                resume_id,
                body.model_dump(),
            )
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return JSONResponse(payload, status_code=status_code)

    @router.delete("/{resume_id}")
    async def delete_resume(resume_id: int):
        payload, status_code = await run_in_threadpool(
            module_provider().delete,
            resume_id,
        )
        return JSONResponse(payload, status_code=status_code)

    @router.get("/{user_id}")
    async def list_resumes(user_id: int):
        try:
            return await run_in_threadpool(module_provider().list, user_id)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    return router


async def _create_upload(
    module: ResumeModule,
    upload: UploadFile,
    *,
    title: str | None,
    requested_user_id: Any,
) -> JSONResponse:
    payload, status_code = await run_in_threadpool(
        module.create_upload,
        upload.file,
        filename=upload.filename or "",
        title=title,
        requested_user_id=requested_user_id,
    )
    return JSONResponse(payload, status_code=status_code)

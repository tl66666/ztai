from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.platform import FileUtilityModule, RuntimeConfigModule


def create_platform_router(
    config_provider: Callable[[], RuntimeConfigModule],
    files_provider: Callable[[], FileUtilityModule],
) -> APIRouter:
    router = APIRouter(tags=["platform"])

    @router.get("/api/career/profiles")
    def career_profiles():
        return config_provider().career_profiles()

    @router.get("/api/config/providers")
    def providers():
        return config_provider().providers()

    @router.post("/api/config/ai-key")
    async def configure_ai(request: Request):
        try:
            return config_provider().configure_ai(await json_object_body(request))
        except ValueError as exc:
            return domain_error_response(exc)

    @router.get("/api/config/ai-status")
    def ai_status():
        return config_provider().ai_status()

    @router.get("/api/questions")
    def questions(category: Annotated[str, Query()] = "general"):
        return config_provider().questions(category)

    @router.post("/api/ai/generate-test-report")
    async def generate_test_report(request: Request):
        try:
            return config_provider().test_report(await json_object_body(request))
        except ValueError as exc:
            return domain_error_response(exc)

    @router.get("/api/uploads/{filename:path}/download/{format_type}")
    async def download_audio(filename: str, format_type: str):
        try:
            path, download_name, media_type = await run_in_threadpool(
                files_provider().audio_download,
                filename,
                format_type,
            )
        except RuntimeError as exc:
            return JSONResponse(
                {"success": False, "message": str(exc)},
                status_code=501,
            )
        except (LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return FileResponse(
            path,
            filename=download_name,
            media_type=media_type,
        )

    @router.get("/api/uploads/{filename:path}")
    async def uploaded_file(filename: str):
        try:
            path, media_type = await run_in_threadpool(files_provider().upload, filename)
        except (LookupError, ValueError) as exc:
            return domain_error_response(exc)
        return FileResponse(path, media_type=media_type)

    @router.post("/api/convert/pdf-to-word")
    async def pdf_to_word(file: Annotated[UploadFile, File()]):
        return await _conversion(
            files_provider().pdf_to_word,
            file,
            failure_prefix="PDF 转 Word 失败",
        )

    @router.post("/api/convert/word-to-pdf")
    async def word_to_pdf(file: Annotated[UploadFile, File()]):
        return await _conversion(
            files_provider().word_to_pdf,
            file,
            failure_prefix="Word 转 PDF 失败",
        )

    return router


async def _conversion(
    operation: Callable,
    upload: UploadFile,
    *,
    failure_prefix: str,
):
    try:
        path, filename = await run_in_threadpool(
            operation,
            upload.file,
            upload.filename or "",
        )
    except ValueError as exc:
        return domain_error_response(exc)
    except Exception as exc:
        return JSONResponse(
            {"success": False, "message": f"{failure_prefix}：{exc}"},
            status_code=500,
        )
    return FileResponse(path, filename=filename)

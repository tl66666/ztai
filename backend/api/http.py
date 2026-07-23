from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from utils.domain import InterviewConflictError


async def json_object_body(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON body must be an object") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def domain_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, InterviewConflictError):
        return JSONResponse(
            {
                "success": False,
                "message": str(exc),
                "code": "interview_stage_conflict",
            },
            status_code=409,
        )
    if isinstance(exc, PermissionError):
        status_code = 403
    elif isinstance(exc, LookupError):
        status_code = 404
    else:
        status_code = 400
    return JSONResponse(
        {"success": False, "message": str(exc)},
        status_code=status_code,
    )

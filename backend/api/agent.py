from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.application.agent import AgentModule
from utils.agent_runtime.actions import ActionProposalError

_LOGGER = logging.getLogger(__name__)
_ACTION_MESSAGES = {
    "execution_failed": "暂时无法保存这项操作，请稍后重试。",
    "execution_uncertain": "暂时无法完成这项操作，请稍后重试。",
    "invalid_state": "这项操作状态已变化，请刷新后再试。",
    "proposal_cancelled": "这项操作已取消。",
    "proposal_expired": "这项操作已过期，请重新生成。",
    "proposal_executing": "操作正在处理中，请稍后查看结果。",
    "proposal_failed": "这项操作未能完成，请重新生成后再试。",
    "proposal_completed": "这项操作已经完成。",
    "draft_not_available": "该操作没有可编辑的简历草稿。",
    "foreign_origin": "请在本机项目页面中完成此操作。",
    "user_id_not_allowed": "当前版本只能操作本机自己的数据。",
    "forbidden": "无法访问这项操作。",
    "not_found": "未找到这项操作，它可能已被清理。",
    "invalid_request": "提交内容不符合要求，请检查后重试。",
    "internal_error": "暂时无法完成这项操作，请稍后重试。",
}


def create_agent_router(
    module_provider: Callable[[], AgentModule],
) -> APIRouter:
    router = APIRouter(prefix="/api/agent", tags=["agent"])

    @router.get("/actions")
    async def list_actions(request: Request):
        return await _action_call(
            module_provider().list_actions,
            _user_id(request),
            request.query_params,
        )

    @router.get("/actions/{proposal_id}")
    async def get_action(proposal_id: int, request: Request):
        return await _action_call(
            module_provider().get_action,
            _user_id(request),
            proposal_id,
            request.query_params,
        )

    @router.get("/actions/{proposal_id}/draft")
    async def get_action_draft(proposal_id: int, request: Request):
        return await _action_call(
            module_provider().get_action_draft,
            _user_id(request),
            proposal_id,
            request.query_params,
        )

    @router.post("/actions/{proposal_id}/edit")
    async def edit_action(proposal_id: int, request: Request):
        return await _action_mutation(
            request,
            module_provider().edit_action,
            proposal_id,
        )

    @router.post("/actions/{proposal_id}/confirm")
    async def confirm_action(proposal_id: int, request: Request):
        return await _action_mutation(
            request,
            module_provider().confirm_action,
            proposal_id,
        )

    @router.post("/actions/{proposal_id}/cancel")
    async def cancel_action(proposal_id: int, request: Request):
        return await _action_mutation(
            request,
            module_provider().cancel_action,
            proposal_id,
        )

    @router.post("/conversations")
    async def create_conversation(request: Request):
        try:
            body = await _object_body(request)
            payload, status = await run_in_threadpool(
                module_provider().create_conversation,
                _user_id(request),
                body,
            )
        except PermissionError:
            return _access_denied()
        except ValueError as exc:
            return _plain_error(str(exc), 400)
        return JSONResponse(payload, status_code=status)

    @router.get("/conversations/{user_id}")
    async def list_conversations(user_id: int, request: Request):
        try:
            payload = await run_in_threadpool(
                module_provider().list_conversations,
                _user_id(request),
                user_id,
            )
        except PermissionError:
            return _access_denied()
        return payload

    @router.get("/conversations/{conversation_id}/messages")
    async def list_messages(conversation_id: str, request: Request):
        try:
            payload, status = await run_in_threadpool(
                module_provider().list_messages,
                _user_id(request),
                conversation_id,
                request.query_params.get("user_id"),
            )
        except PermissionError:
            return _access_denied()
        return JSONResponse(payload, status_code=status)

    @router.post("/conversations/{conversation_id}/clear")
    async def clear_conversation(conversation_id: str, request: Request):
        try:
            body = await _object_body(request)
            payload, status = await run_in_threadpool(
                module_provider().clear_conversation,
                _user_id(request),
                conversation_id,
                body,
            )
        except PermissionError:
            return _access_denied()
        except ValueError as exc:
            return _plain_error(str(exc), 400)
        return JSONResponse(payload, status_code=status)

    @router.post("/chat")
    async def chat(request: Request):
        try:
            body = await _json_body(request)
            payload, status = await run_in_threadpool(
                module_provider().chat,
                _user_id(request),
                body,
            )
        except PermissionError:
            return _access_denied()
        return JSONResponse(payload, status_code=status)

    @router.post("/clear-memory")
    async def clear_memory(request: Request):
        try:
            body = await _object_body(request)
            payload, status = await run_in_threadpool(
                module_provider().clear_memory,
                _user_id(request),
                body,
            )
        except PermissionError:
            return _access_denied()
        except ValueError as exc:
            return _plain_error(str(exc), 400)
        return JSONResponse(payload, status_code=status)

    return router


async def _action_mutation(
    request: Request,
    operation: Callable,
    proposal_id: int,
) -> JSONResponse | dict[str, Any]:
    try:
        body = await _strict_action_body(request)
    except Exception as exc:
        return _action_error(exc)
    return await _action_call(
        operation,
        _user_id(request),
        proposal_id,
        body,
        request.headers,
    )


async def _action_call(operation: Callable, *args):
    try:
        return await run_in_threadpool(operation, *args)
    except Exception as exc:
        return _action_error(exc)


def _action_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, ActionProposalError):
        status = exc.http_status
        code = exc.code
        if status >= 500:
            _LOGGER.exception("Agent action failed with code %s", code)
    elif isinstance(exc, PermissionError):
        status, code = 403, "forbidden"
    elif isinstance(exc, LookupError):
        status, code = 404, "not_found"
    elif isinstance(exc, ValueError):
        status, code = 400, "invalid_request"
    else:
        _LOGGER.exception("Unexpected agent action API failure")
        status, code = 500, "internal_error"
    return JSONResponse(
        {
            "success": False,
            "error": {
                "code": code,
                "message": _ACTION_MESSAGES.get(
                    code,
                    "暂时无法完成这项操作，请稍后重试。",
                ),
            },
        },
        status_code=status,
    )


async def _strict_action_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    if content_type.lower() != "application/json":
        raise ValueError("Content-Type must be application/json")
    body = await _json_body(request)
    if not isinstance(body, dict):
        raise ValueError("JSON body must be an object")
    return body


async def _object_body(request: Request) -> dict[str, Any]:
    body = await _json_body(request)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ValueError("JSON body must be an object")
    return body


async def _json_body(request: Request) -> Any:
    raw = await request.body()
    if not raw:
        return None
    try:
        return await request.json()
    except Exception:
        return None


def _user_id(request: Request) -> int:
    return int(request.state.principal.user_id)


def _access_denied() -> JSONResponse:
    return _plain_error("当前本地版本仅允许访问当前用户数据", 403)


def _plain_error(message: str, status: int) -> JSONResponse:
    return JSONResponse(
        {"success": False, "message": message},
        status_code=status,
    )

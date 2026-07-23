from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from backend.adapters.persistence.agent import AgentRepository
from utils.agent_runtime.actions import (
    ActionProposalError,
    ActionProposalService,
)
from utils.agent_runtime.memory import is_browser_event_artifact
from utils.agent_runtime.service import AgentService

AGENT_CONTEXT_MODULES = frozenset(
    {
        "home",
        "resume",
        "resume:input",
        "resume:manage",
        "resume:analysis",
        "resume:export",
        "resume:jd",
        "resume:skills",
        "interview",
        "interview:mock",
        "interview:professional",
        "interview:practice",
        "interview:records",
        "tracker",
        "tracker:add",
        "tracker:board",
        "tracker:salary",
        "agent",
    }
)


class AgentModule:
    """Own Agent HTTP use cases behind a compact application interface."""

    def __init__(
        self,
        service: AgentService,
        action_service: ActionProposalService,
        repository: AgentRepository,
        *,
        local_user_id: int,
        allowed_origins: tuple[str, ...],
    ):
        self.service = service
        self.action_service = action_service
        self._repository = repository
        self._local_user_id = int(local_user_id)
        self._allowed_origins = frozenset(allowed_origins)

    def list_actions(
        self,
        principal_user_id: int,
        query: Mapping[str, str],
    ) -> dict[str, Any]:
        user_id = self._action_user(principal_user_id, query=query)
        status = query.get("status", "pending")
        if status != "pending":
            raise ValueError("only pending actions can be listed")
        actions = self.action_service.list_pending(user_id)
        return {
            "success": True,
            "actions": [self.action_service.public(item) for item in actions],
        }

    def get_action(
        self,
        principal_user_id: int,
        proposal_id: int,
        query: Mapping[str, str],
    ) -> dict[str, Any]:
        user_id = self._action_user(principal_user_id, query=query)
        action = self.action_service.get(user_id, proposal_id)
        return {"success": True, "action": self.action_service.public(action)}

    def get_action_draft(
        self,
        principal_user_id: int,
        proposal_id: int,
        query: Mapping[str, str],
    ) -> dict[str, Any]:
        user_id = self._action_user(principal_user_id, query=query)
        draft = self.action_service.draft(user_id, proposal_id)
        return {"success": True, "draft": draft}

    def edit_action(
        self,
        principal_user_id: int,
        proposal_id: int,
        body: dict[str, Any],
        headers: Mapping[str, str],
    ) -> dict[str, Any]:
        self._require_action_origin(headers)
        user_id = self._action_user(principal_user_id, body=body)
        action = self.action_service.edit(user_id, proposal_id, body)
        return {"success": True, "action": self.action_service.public(action)}

    def confirm_action(
        self,
        principal_user_id: int,
        proposal_id: int,
        body: dict[str, Any],
        headers: Mapping[str, str],
    ) -> dict[str, Any]:
        self._require_action_origin(headers)
        user_id = self._action_user(principal_user_id, body=body)
        if body:
            raise ValueError("confirm does not accept changes")
        action = self.action_service.confirm(user_id, proposal_id)
        return {
            "success": True,
            "action": self.action_service.public(action),
            "result": action["result"],
        }

    def cancel_action(
        self,
        principal_user_id: int,
        proposal_id: int,
        body: dict[str, Any],
        headers: Mapping[str, str],
    ) -> dict[str, Any]:
        self._require_action_origin(headers)
        user_id = self._action_user(principal_user_id, body=body)
        if body:
            raise ValueError("cancel does not accept changes")
        action = self.action_service.cancel(user_id, proposal_id)
        return {"success": True, "action": self.action_service.public(action)}

    def create_conversation(
        self,
        principal_user_id: int,
        body: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        user_id = self._conversation_user(principal_user_id, body.get("user_id"))
        conversation = self.service.create_conversation(
            user_id,
            body.get("title", "新对话"),
        )
        return {"success": True, "conversation": conversation}, 201

    def list_conversations(
        self,
        principal_user_id: int,
        requested_user_id: int,
    ) -> dict[str, Any]:
        user_id = self._conversation_user(principal_user_id, requested_user_id)
        return {
            "success": True,
            "conversations": self.service.list_conversations(user_id),
        }

    def list_messages(
        self,
        principal_user_id: int,
        conversation_id: str,
        requested_user_id: Any,
    ) -> tuple[dict[str, Any], int]:
        user_id = self._conversation_user(principal_user_id, requested_user_id)
        messages = self.service.list_messages(conversation_id, user_id)
        if messages is None:
            return {"success": False, "message": "会话不存在"}, 404
        return {"success": True, "messages": messages}, 200

    def clear_conversation(
        self,
        principal_user_id: int,
        conversation_id: str,
        body: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        user_id = self._conversation_user(principal_user_id, body.get("user_id"))
        if not self.service.clear_conversation(conversation_id, user_id):
            return {"success": False, "message": "会话不存在"}, 404
        return {"success": True, "message": "当前会话已清空"}, 200

    def chat(
        self,
        principal_user_id: int,
        body: Any,
    ) -> tuple[dict[str, Any], int]:
        self._require_principal(principal_user_id)
        if not isinstance(body, dict):
            return self._message_error()
        if set(body) - {"message", "conversation_id", "context"}:
            return {
                "success": False,
                "message": "请求只能包含消息、会话和上下文",
            }, 400
        raw_message = body.get("message")
        if not isinstance(raw_message, str):
            return self._message_error()
        message = raw_message.strip()
        if not message or len(message) > 12000:
            return self._message_error()
        if is_browser_event_artifact(message):
            return {
                "success": False,
                "message": "点击已忽略，请在输入框中写下你的问题后再发送",
            }, 400

        conversation_id = body.get("conversation_id", "")
        if not isinstance(conversation_id, str) or len(conversation_id) > 200:
            return {"success": False, "message": "会话标识无效"}, 400
        context = body["context"] if "context" in body else {}
        context_error = self._validate_context(context)
        if context_error:
            return {"success": False, "message": context_error}, 400
        if not self._repository.context_entities_exist(
            principal_user_id,
            resume_id=context.get("resume_id"),
            opportunity_id=context.get("opportunity_id"),
        ):
            return {"success": False, "message": "上下文实体不存在"}, 404
        try:
            result = self.service.chat(
                user_id=principal_user_id,
                message=message,
                conversation_id=conversation_id,
                context=context,
            )
        except ValueError:
            return {"success": False, "message": "会话不存在"}, 404
        return {
            "success": True,
            "reply": result["reply"],
            "ai_used": result["ai_used"],
            "conversation_id": result["conversation_id"],
            "status": result["status"],
            "events": result["events"],
            "agent_trace": result["events"],
            "tools_used": result["tools_used"],
            "action_proposals": result["action_proposals"],
            "input_request": result.get("input_request", {}),
            "iterations": max(1, len(result["tools_used"])),
            "suggested_actions": result["suggested_actions"],
            "provider": "structured-agent-runtime",
        }, 200

    def clear_memory(
        self,
        principal_user_id: int,
        body: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        conversation_id = str(body.get("conversation_id", ""))
        user_id = self._conversation_user(principal_user_id, body.get("user_id"))
        if not conversation_id:
            return {"success": False, "message": "请提供 conversation_id"}, 400
        if not self.service.clear_conversation(conversation_id, user_id):
            return {"success": False, "message": "会话不存在"}, 404
        return {"success": True, "message": "当前会话已清空"}, 200

    def _require_principal(self, principal_user_id: int) -> int:
        if int(principal_user_id) != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")
        return self._local_user_id

    def _conversation_user(
        self,
        principal_user_id: int,
        requested_user_id: Any,
    ) -> int:
        self._require_principal(principal_user_id)
        if requested_user_id is None:
            return self._local_user_id
        try:
            user_id = int(requested_user_id)
        except (TypeError, ValueError) as exc:
            raise PermissionError(
                "当前本地版本仅允许访问当前用户数据"
            ) from exc
        if user_id != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")
        return user_id

    def _action_user(
        self,
        principal_user_id: int,
        *,
        query: Mapping[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> int:
        self._require_principal(principal_user_id)
        if (query is not None and "user_id" in query) or (
            body is not None and "user_id" in body
        ):
            raise ActionProposalError(
                "user_id_not_allowed",
                "user_id is controlled by the server",
                400,
            )
        return self._local_user_id

    def _require_action_origin(self, headers: Mapping[str, str]) -> None:
        supplied = headers.get("origin")
        if not supplied:
            referer = headers.get("referer")
            if referer:
                parsed = urlsplit(referer)
                supplied = f"{parsed.scheme}://{parsed.netloc}"
        if supplied and supplied not in self._allowed_origins:
            raise ActionProposalError(
                "foreign_origin",
                "state changes require an allowed UI origin",
                403,
            )

    @staticmethod
    def _message_error() -> tuple[dict[str, Any], int]:
        return {
            "success": False,
            "message": "消息必须是 1 到 12000 个字符",
        }, 400

    @staticmethod
    def _validate_context(context: Any) -> str | None:
        if not isinstance(context, dict) or set(context) - {
            "module",
            "opportunity_id",
            "resume_id",
        }:
            return "上下文只能包含当前模块和实体 ID"
        module = context.get("module")
        if module is not None and module not in AGENT_CONTEXT_MODULES:
            return "上下文模块不存在"
        for field in ("opportunity_id", "resume_id"):
            value = context.get(field)
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                return "上下文只能包含当前模块和实体 ID"
        return None

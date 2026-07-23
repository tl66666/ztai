from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import requests

from backend.adapters.persistence.sqlalchemy.agent_session import (
    AgentSessionProvider,
    SessionFactory,
)
from backend.adapters.persistence.sqlalchemy.agent_tool_store import (
    SqlAlchemyAgentToolStore,
)
from utils.agent_runtime.models import ToolResult
from utils.domain.career import CareerService
from utils.domain.interviews import InterviewService

from .tool_schema import validate_tool_arguments


def _default_ai_client_provider():
    # Keep the historical patch point lazy without making the registry depend
    # on the compatibility facade during module import.
    from . import tools

    return tools.get_ai_client()


@dataclass(frozen=True)
class ToolContext:
    user_id: int
    db_path: str
    deadline: float
    ai_client_provider: Callable
    persistence: SqlAlchemyAgentToolStore
    session_factory: SessionFactory
    career_service: CareerService
    interview_service: InterviewService

    def remaining_seconds(self) -> float:
        return self.deadline - time.monotonic()

    def check_timeout(self) -> None:
        if self.remaining_seconds() <= 0:
            raise ToolTimeoutError("tool deadline exceeded")

    def request_timeout(self, maximum: float) -> float:
        self.check_timeout()
        return max(0.1, min(maximum, self.remaining_seconds()))


class ToolTimeoutError(TimeoutError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    executor: Callable[[dict, ToolContext], ToolResult]
    read_only: bool = True
    timeout_seconds: int = 10


class ToolRegistry:
    def __init__(
        self,
        db_path: str,
        local_user_id: int = 1,
        ai_client_provider: Callable | None = None,
        session_factory: SessionFactory | None = None,
        career_service: CareerService | None = None,
        interview_service: InterviewService | None = None,
    ):
        self.db_path = db_path
        self.local_user_id = int(local_user_id)
        self.ai_client_provider = ai_client_provider or _default_ai_client_provider
        self._sessions = AgentSessionProvider(
            db_path,
            session_factory=session_factory,
        )
        self._persistence = SqlAlchemyAgentToolStore(self._sessions)
        self._career_service = career_service or CareerService(
            db_path,
            local_user_id=self.local_user_id,
        )
        self._interview_service = interview_service or InterviewService(
            db_path,
            self.local_user_id,
            session_factory=(
                self._sessions.session_factory if session_factory is not None else None
            ),
        )
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def schemas(self, names: list[str] | None = None) -> list[dict]:
        selected = [tool for tool in self._tools.values() if names is None or tool.name in names]
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in selected
        ]

    def execute(
        self,
        name: str,
        arguments: dict,
        user_id: int,
        timeout_seconds: float | None = None,
    ) -> ToolResult:
        definition = self._tools.get(name)
        if not definition:
            return ToolResult(False, display_text="未知工具", error_code="unknown_tool")
        if not isinstance(arguments, dict):
            return ToolResult(
                False,
                display_text="工具参数必须是 JSON 对象",
                error_code="invalid_arguments",
            )
        try:
            runtime_user_id = int(user_id)
        except (TypeError, ValueError):
            runtime_user_id = -1
        if runtime_user_id != self.local_user_id:
            return ToolResult(
                False,
                display_text="当前工具仅允许本地用户访问",
                error_code="forbidden",
            )
        safe_arguments = {key: value for key, value in arguments.items() if key != "user_id"}
        errors = validate_tool_arguments(definition.parameters, safe_arguments)
        if errors:
            return ToolResult(
                False,
                data={"errors": errors},
                display_text="；".join(errors),
                error_code="invalid_arguments",
            )
        try:
            effective_timeout = definition.timeout_seconds
            if timeout_seconds is not None:
                effective_timeout = min(effective_timeout, max(0.01, timeout_seconds))
            context = ToolContext(
                user_id=self.local_user_id,
                db_path=self.db_path,
                deadline=time.monotonic() + effective_timeout,
                ai_client_provider=self.ai_client_provider,
                persistence=self._persistence,
                session_factory=self._sessions.session_factory,
                career_service=self._career_service,
                interview_service=self._interview_service,
            )
            result = definition.executor(safe_arguments, context)
            context.check_timeout()
            return result
        except ToolTimeoutError:
            return ToolResult(
                False,
                display_text=f"工具 {name} 执行超时",
                error_code="tool_timeout",
                retryable=True,
            )
        except LookupError:
            return ToolResult(False, display_text="未找到可读取的数据", error_code="not_found")
        except PermissionError:
            return ToolResult(False, display_text="无权读取该数据", error_code="forbidden")
        except (ValueError, TypeError):
            return ToolResult(
                False, display_text="工具参数无效", error_code="invalid_arguments", retryable=False
            )
        except requests.RequestException:
            return ToolResult(
                False,
                display_text="网络请求失败",
                error_code="network_error",
                retryable=True,
            )
        except Exception:
            return ToolResult(
                False,
                display_text=f"工具 {name} 执行失败",
                error_code="tool_error",
                retryable=False,
            )

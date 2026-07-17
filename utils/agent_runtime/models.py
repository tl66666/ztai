from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: int
    title: str
    status: str = "active"
    summary: str = ""


@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: str
    user_id: int
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any = None
    display_text: str = ""
    error_code: str = ""
    retryable: bool = False


@dataclass(frozen=True)
class AgentDecision:
    type: str
    tool: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    call_id: str = ""


@dataclass(frozen=True)
class AgentRunResult:
    reply: str
    status: str
    conversation_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    action_proposals: list[dict[str, Any]] = field(default_factory=list)
    input_request: dict[str, Any] = field(default_factory=dict)
    ai_used: bool = False

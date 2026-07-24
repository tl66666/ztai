from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from urllib.parse import urlparse

import requests

from backend.adapters.persistence.sqlalchemy.agent_session import SessionFactory
from utils.agent_runtime.actions import (
    PROPOSAL_STATUSES,
    ActionProposalService,
    career_action_tool_schema,
)
from utils.agent_runtime.models import ToolResult
from utils.ai_client import get_ai_client as get_ai_client
from utils.domain.career import ACTION_STATUSES, CareerService
from utils.domain.interviews import InterviewService

from .tool_business import (
    _analyze_jd,
    _analyze_resume,
    _career_profile,
    _career_report,
    _dashboard,
    _diagnose_resume,
    _evaluate_answer,
    _evaluate_salary,
    _get_resume,
    _interview_question,
    _list_action_items,
    _list_applications,
    _list_resumes,
    _match_job,
    _opportunity,
    _prepare_resume_revision,
    _resume_interview_questions,
    _training_insights,
)
from .tool_registry import (
    ToolContext,
    ToolDefinition,
    ToolRegistry,
)
from .tool_registry import (
    ToolTimeoutError as ToolTimeoutError,
)


def _object(properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _list_agent_actions(arguments: dict, context: ToolContext) -> ToolResult:
    service = ActionProposalService(
        context.db_path,
        local_user_id=context.user_id,
        session_factory=context.session_factory,
    )
    proposals = service.list_actions(context.user_id, arguments.get("status"))
    data = [service.public(item) for item in proposals]
    text = "\n".join(f"#{item['id']} {item['preview']} / {item['status']}" for item in data)
    return ToolResult(True, data=data, display_text=text or "暂无操作提案")


def _propose_career_action(arguments: dict, context: ToolContext) -> ToolResult:
    service = ActionProposalService(
        context.db_path,
        local_user_id=context.user_id,
        session_factory=context.session_factory,
    )
    proposal = service.propose(
        context.user_id,
        arguments["action_type"],
        arguments["arguments"],
        rationale=arguments.get("rationale", ""),
    )
    public = service.public(proposal)
    return ToolResult(
        True,
        data=public,
        display_text=f"已生成待确认操作：{public['preview']}。请在操作卡片中确认或取消。",
    )


def _web_search(arguments: dict, context: ToolContext) -> ToolResult:
    query = arguments["query"]
    response = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_html": "1"},
        timeout=context.request_timeout(8),
        headers={"User-Agent": "JobHunterAI/1.0"},
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    if payload.get("AbstractText"):
        results.append(
            {
                "title": payload.get("Heading") or query,
                "snippet": payload["AbstractText"],
                "url": payload.get("AbstractURL", ""),
            }
        )
    for item in payload.get("RelatedTopics", [])[:5]:
        if isinstance(item, dict) and item.get("Text"):
            results.append(
                {
                    "title": item["Text"][:80],
                    "snippet": item["Text"],
                    "url": item.get("FirstURL", ""),
                }
            )
    return ToolResult(
        bool(results),
        data=results,
        display_text="\n".join(item["snippet"] for item in results) or "未找到结果",
        error_code="" if results else "not_found",
    )


def _is_safe_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
            )
        }
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            return False
    return True


def _fetch_webpage(arguments: dict, context: ToolContext) -> ToolResult:
    url = arguments["url"]
    if not _is_safe_public_url(url):
        return ToolResult(
            False, display_text="拒绝访问本机、内网或无效地址", error_code="unsafe_url"
        )
    response = requests.get(
        url,
        timeout=context.request_timeout(10),
        headers={"User-Agent": "JobHunterAI/1.0"},
        allow_redirects=False,
        stream=True,
    )
    try:
        response.raise_for_status()
        if "text/" not in response.headers.get("Content-Type", ""):
            return ToolResult(
                False, display_text="仅支持抓取文本网页", error_code="unsupported_content"
            )
        chunks = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            remaining = 262144 - len(chunks)
            if remaining <= 0:
                break
            chunks.extend(chunk[:remaining])
            if len(chunks) >= 262144:
                break
        content = bytes(chunks).decode(response.encoding or "utf-8", errors="replace")
    finally:
        response.close()
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.I | re.S)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", content)).strip()[:6000]
    return ToolResult(
        bool(text),
        data={"url": url, "text": text},
        display_text=text,
        error_code="" if text else "empty_content",
    )


def build_tool_registry(
    db_path: str,
    *,
    ai_client_provider: Callable | None = None,
    session_factory: SessionFactory | None = None,
    career_service: CareerService | None = None,
    interview_service: InterviewService | None = None,
) -> ToolRegistry:
    registry = ToolRegistry(
        db_path,
        ai_client_provider=ai_client_provider,
        session_factory=session_factory,
        career_service=career_service,
        interview_service=interview_service,
    )
    definitions = [
        ToolDefinition("list_resumes", "列出当前用户保存的简历元数据。", _object(), _list_resumes),
        ToolDefinition(
            "get_resume",
            "读取当前用户指定或最近一份简历的完整正文。",
            _object({"resume_id": {"type": "integer"}}),
            _get_resume,
        ),
        ToolDefinition(
            "analyze_resume",
            "基于简历正文执行即时、本地优先的质量诊断，不等待第二次模型调用。",
            _object(
                {"resume_id": {"type": "integer"}, "job_title": {"type": "string", "maxLength": 80}}
            ),
            _analyze_resume,
        ),
        ToolDefinition(
            "diagnose_resume",
            "对指定简历执行本地优先诊断；无模型密钥也会检查结构、证据和岗位对齐。",
            _object(
                {
                    "resume_id": {"type": "integer", "minimum": 1},
                    "job_title": {"type": "string", "maxLength": 80},
                },
                ["resume_id"],
            ),
            _diagnose_resume,
        ),
        ToolDefinition(
            "prepare_resume_revision",
            "有模型配置时通读完整简历进行深度改写；无配置时生成事实保真草稿；只生成待确认内容，不保存。",
            _object(
                {
                    "resume_id": {"type": "integer", "minimum": 1},
                    "target_job_title": {"type": "string", "maxLength": 80},
                },
                ["resume_id"],
            ),
            _prepare_resume_revision,
            timeout_seconds=45,
        ),
        ToolDefinition(
            "match_job",
            "基于简历和 JD 关键词即时生成可解释的岗位匹配素材。",
            _object(
                {
                    "resume_id": {"type": "integer"},
                    "job_title": {"type": "string", "minLength": 2, "maxLength": 80},
                    "jd": {"type": "string", "maxLength": 8000},
                },
                ["job_title"],
            ),
            _match_job,
        ),
        ToolDefinition(
            "analyze_jd",
            "即时提取岗位 JD 的关键词、职责摘录和准备方向。",
            _object(
                {"jd_text": {"type": "string", "minLength": 10, "maxLength": 10000}}, ["jd_text"]
            ),
            _analyze_jd,
        ),
        ToolDefinition(
            "get_interview_question",
            "获取指定方向的一道面试题。",
            _object({"category": {"type": "string", "maxLength": 30}}),
            _interview_question,
        ),
        ToolDefinition(
            "generate_resume_interview_questions",
            "根据指定简历生成多道定制面试题，只返回题目和练习建议。",
            _object({"resume_id": {"type": "integer", "minimum": 1}}, ["resume_id"]),
            _resume_interview_questions,
        ),
        ToolDefinition(
            "evaluate_answer",
            "评估用户的面试回答。",
            _object(
                {
                    "question": {"type": "string", "minLength": 2, "maxLength": 1000},
                    "answer": {"type": "string", "minLength": 1, "maxLength": 6000},
                },
                ["question", "answer"],
            ),
            _evaluate_answer,
        ),
        ToolDefinition(
            "evaluate_salary",
            "按城市、经验和技能数量给出规则估算薪资区间。",
            _object(
                {
                    "city": {"type": "string", "maxLength": 20},
                    "experience": {
                        "type": "string",
                        "enum": ["应届生", "1-3年", "3-5年", "5年以上"],
                    },
                    "skills_count": {"type": "integer"},
                }
            ),
            _evaluate_salary,
        ),
        ToolDefinition(
            "list_applications", "读取当前用户的投递记录。", _object(), _list_applications
        ),
        ToolDefinition(
            "get_dashboard", "读取当前用户简历、匹配、面试和投递统计。", _object(), _dashboard
        ),
        ToolDefinition(
            "generate_career_report",
            "汇总当前用户求职数据形成阶段报告素材。",
            _object(),
            _career_report,
        ),
        ToolDefinition(
            "get_career_profile", "读取当前用户已确认的职业档案。", _object(), _career_profile
        ),
        ToolDefinition(
            "get_opportunity",
            "读取当前用户指定的未删除投递机会。",
            _object({"opportunity_id": {"type": "integer"}}, ["opportunity_id"]),
            _opportunity,
        ),
        ToolDefinition(
            "get_training_insights",
            "汇总最近完成的面试、题库和语音训练质量，不返回回答、反馈全文或音频内容。",
            _object(),
            _training_insights,
        ),
        ToolDefinition(
            "list_action_items",
            "读取当前用户行动项，可按状态筛选。",
            _object({"status": {"type": "string", "enum": list(ACTION_STATUSES)}}),
            _list_action_items,
        ),
        ToolDefinition(
            "list_agent_actions",
            "读取当前用户的操作提案，只返回脱敏公开字段。",
            _object({"status": {"type": "string", "enum": sorted(PROPOSAL_STATUSES)}}),
            _list_agent_actions,
        ),
        ToolDefinition(
            "propose_career_action",
            "创建待用户在界面确认的职业操作提案；本工具不会执行、确认或取消操作。",
            career_action_tool_schema(),
            _propose_career_action,
            read_only=False,
        ),
        ToolDefinition(
            "web_search",
            "搜索需要时效性的公开互联网信息。",
            _object({"query": {"type": "string", "minLength": 2, "maxLength": 200}}, ["query"]),
            _web_search,
        ),
        ToolDefinition(
            "fetch_webpage",
            "读取指定公开网页的文本内容。",
            _object({"url": {"type": "string", "minLength": 8, "maxLength": 2000}}, ["url"]),
            _fetch_webpage,
        ),
    ]
    for definition in definitions:
        registry.register(definition)
    return registry

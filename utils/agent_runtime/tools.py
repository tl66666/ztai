from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import random
import re
import socket
import sqlite3
import time
from typing import Callable
from urllib.parse import urlparse

import requests

from utils.agent_runtime.memory import ClosingConnection
from utils.agent_runtime.models import ToolResult
from utils.ai_client import get_ai_client


@dataclass(frozen=True)
class ToolContext:
    user_id: int
    db_path: str
    deadline: float

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


def _validate(schema: dict, arguments: dict) -> list[str]:
    if not isinstance(arguments, dict):
        return ["参数必须是对象"]
    errors = []
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in arguments or arguments[key] in (None, ""):
            errors.append(f"缺少参数 {key}")
    type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool}
    for key, value in arguments.items():
        rule = properties.get(key)
        if not rule or key == "user_id":
            continue
        expected = type_map.get(rule.get("type"))
        if expected and (not isinstance(value, expected) or isinstance(value, bool) and rule.get("type") != "boolean"):
            errors.append(f"参数 {key} 类型错误")
            continue
        if isinstance(value, str):
            if len(value) < rule.get("minLength", 0):
                errors.append(f"参数 {key} 太短")
            if len(value) > rule.get("maxLength", 1000000):
                errors.append(f"参数 {key} 太长")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"参数 {key} 不在允许范围")
    return errors


class ToolRegistry:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def schemas(self, names: list[str] | None = None) -> list[dict]:
        selected = [
            tool for tool in self._tools.values()
            if names is None or tool.name in names
        ]
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
        safe_arguments = {key: value for key, value in arguments.items() if key != "user_id"}
        errors = _validate(definition.parameters, safe_arguments)
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
                user_id=int(user_id),
                db_path=self.db_path,
                deadline=time.monotonic() + effective_timeout,
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
        except (sqlite3.Error, ValueError, TypeError) as exc:
            return ToolResult(False, display_text=str(exc), error_code="tool_error", retryable=False)
        except requests.RequestException as exc:
            return ToolResult(False, display_text=str(exc), error_code="network_error", retryable=True)
        except Exception:
            return ToolResult(
                False,
                display_text=f"工具 {name} 执行失败",
                error_code="tool_error",
                retryable=False,
            )


def _object(properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    return connection


def _list_resumes(arguments: dict, context: ToolContext) -> ToolResult:
    with _connect(context.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, title, substr(content, 1, 180) AS preview, updated_at
            FROM resumes WHERE user_id = ? ORDER BY updated_at DESC LIMIT 10
            """,
            (context.user_id,),
        ).fetchall()
    data = [dict(row) for row in rows]
    text = "\n".join(f"#{row['id']} {row['title']}：{row['preview']}" for row in data)
    return ToolResult(True, data=data, display_text=text or "暂无已保存简历")


def _get_resume(arguments: dict, context: ToolContext) -> ToolResult:
    resume_id = arguments.get("resume_id")
    with _connect(context.db_path) as connection:
        if resume_id is None:
            row = connection.execute(
                "SELECT id, user_id, title, content, updated_at FROM resumes WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
                (context.user_id,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT id, user_id, title, content, updated_at FROM resumes WHERE id = ? AND user_id = ?",
                (resume_id, context.user_id),
            ).fetchone()
    if not row:
        return ToolResult(False, display_text="未找到可读取的简历", error_code="not_found")
    data = dict(row)
    return ToolResult(True, data=data, display_text=f"简历：{data['title']}\n{data['content']}")


def _owned_resume(arguments: dict, context: ToolContext) -> ToolResult:
    return _get_resume({"resume_id": arguments.get("resume_id")}, context)


def _analyze_resume(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    result = get_ai_client().analyze_resume(
        resume.data["content"],
        arguments.get("job_title", ""),
        timeout=context.request_timeout(45),
    )
    content = result.get("content", "")
    return ToolResult(bool(content), data={"resume_id": resume.data["id"], "analysis": content}, display_text=content)


def _match_job(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    result = get_ai_client().match_job(
        resume.data["content"], arguments["job_title"], arguments.get("jd", ""),
        timeout=context.request_timeout(45),
    )
    content = result.get("content", "")
    return ToolResult(bool(content), data={"resume_id": resume.data["id"], "analysis": content}, display_text=content)


def _analyze_jd(arguments: dict, context: ToolContext) -> ToolResult:
    jd = arguments["jd_text"]
    result = get_ai_client().chat([
        {"role": "system", "content": "你是岗位分析专家。提取核心职责、必备技能、加分项和面试重点。"},
        {"role": "user", "content": jd[:5000]},
    ], temperature=0.2, timeout=context.request_timeout(45))
    content = result.get("content", "")
    return ToolResult(bool(content), data={"analysis": content}, display_text=content)


def _interview_question(arguments: dict, context: ToolContext) -> ToolResult:
    from config import INTERVIEW_QUESTIONS

    category = arguments.get("category", "general")
    questions = INTERVIEW_QUESTIONS.get(category) or INTERVIEW_QUESTIONS.get("general", [])
    if not questions:
        return ToolResult(False, display_text="暂无对应面试题", error_code="not_found")
    question = random.choice(questions)
    data = question if isinstance(question, dict) else {"question": str(question)}
    return ToolResult(True, data=data, display_text=data.get("question", ""))


def _evaluate_answer(arguments: dict, context: ToolContext) -> ToolResult:
    from utils.interview_engine import InterviewEngine

    engine = InterviewEngine()
    engine.candidate_answers = [arguments["answer"]]
    result = engine.evaluate()
    return ToolResult(True, data=result, display_text=f"评分：{result['score']}分\n{result['feedback']}")


def _evaluate_salary(arguments: dict, context: ToolContext) -> ToolResult:
    city = arguments.get("city", "")
    experience = arguments.get("experience", "应届生")
    skills_count = arguments.get("skills_count", 0)
    factor = {"北京": 1.25, "上海": 1.25, "深圳": 1.2, "广州": 1.05, "杭州": 1.15, "成都": .9}.get(city, 1)
    base = {"应届生": 9000, "1-3年": 15000, "3-5年": 24000, "5年以上": 36000}.get(experience, 12000)
    average = int((base + min(5000, skills_count * 500)) * factor)
    data = {"city": city, "experience": experience, "minimum": int(average * .75), "maximum": int(average * 1.35), "average": average, "estimate_only": True}
    return ToolResult(True, data=data, display_text=f"规则估算：{data['minimum']}-{data['maximum']} 元/月（非实时行情）")


def _list_applications(arguments: dict, context: ToolContext) -> ToolResult:
    with _connect(context.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, company, job_title, status, city, updated_at
            FROM job_applications
            WHERE user_id = ? AND deleted_at IS NULL
            ORDER BY updated_at DESC LIMIT 20
            """,
            (context.user_id,),
        ).fetchall()
    data = [dict(row) for row in rows]
    text = "\n".join(f"{row['company']} / {row['job_title']} / {row['status']}" for row in data)
    return ToolResult(True, data=data, display_text=text or "暂无投递记录")


def _dashboard(arguments: dict, context: ToolContext) -> ToolResult:
    with _connect(context.db_path) as connection:
        counts = {
            "resumes": connection.execute("SELECT COUNT(*) FROM resumes WHERE user_id = ?", (context.user_id,)).fetchone()[0],
            "matches": connection.execute("SELECT COUNT(*) FROM job_matches WHERE user_id = ?", (context.user_id,)).fetchone()[0],
            "interviews": connection.execute("SELECT COUNT(*) FROM interviews WHERE user_id = ?", (context.user_id,)).fetchone()[0],
            "applications": connection.execute(
                "SELECT COUNT(*) FROM job_applications WHERE user_id = ? AND deleted_at IS NULL",
                (context.user_id,),
            ).fetchone()[0],
        }
    text = "；".join(f"{key}={value}" for key, value in counts.items())
    return ToolResult(True, data=counts, display_text=text)


def _career_report(arguments: dict, context: ToolContext) -> ToolResult:
    dashboard = _dashboard({}, context)
    applications = _list_applications({}, context)
    data = {"dashboard": dashboard.data, "applications": applications.data[:8]}
    text = f"求职概况：{dashboard.display_text}\n最近投递：\n{applications.display_text}"
    return ToolResult(True, data=data, display_text=text)


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
        results.append({"title": payload.get("Heading") or query, "snippet": payload["AbstractText"], "url": payload.get("AbstractURL", "")})
    for item in payload.get("RelatedTopics", [])[:5]:
        if isinstance(item, dict) and item.get("Text"):
            results.append({"title": item["Text"][:80], "snippet": item["Text"], "url": item.get("FirstURL", "")})
    return ToolResult(bool(results), data=results, display_text="\n".join(item["snippet"] for item in results) or "未找到结果", error_code="" if results else "not_found")


def _is_safe_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
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
        return ToolResult(False, display_text="拒绝访问本机、内网或无效地址", error_code="unsafe_url")
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
            return ToolResult(False, display_text="仅支持抓取文本网页", error_code="unsupported_content")
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
    return ToolResult(bool(text), data={"url": url, "text": text}, display_text=text, error_code="" if text else "empty_content")


def build_tool_registry(db_path: str) -> ToolRegistry:
    registry = ToolRegistry(db_path)
    definitions = [
        ToolDefinition("list_resumes", "列出当前用户保存的简历元数据。", _object(), _list_resumes),
        ToolDefinition("get_resume", "读取当前用户指定或最近一份简历的完整正文。", _object({"resume_id": {"type": "integer"}}), _get_resume),
        ToolDefinition("analyze_resume", "分析已保存简历的质量与改进方向。", _object({"resume_id": {"type": "integer"}, "job_title": {"type": "string", "maxLength": 80}}), _analyze_resume),
        ToolDefinition("match_job", "将已保存简历与目标岗位和 JD 匹配。", _object({"resume_id": {"type": "integer"}, "job_title": {"type": "string", "minLength": 2, "maxLength": 80}, "jd": {"type": "string", "maxLength": 8000}}, ["job_title"]), _match_job),
        ToolDefinition("analyze_jd", "解析岗位 JD 的职责、技能和面试重点。", _object({"jd_text": {"type": "string", "minLength": 10, "maxLength": 10000}}, ["jd_text"]), _analyze_jd),
        ToolDefinition("get_interview_question", "获取指定方向的一道面试题。", _object({"category": {"type": "string", "maxLength": 30}}), _interview_question),
        ToolDefinition("evaluate_answer", "评估用户的面试回答。", _object({"question": {"type": "string", "minLength": 2, "maxLength": 1000}, "answer": {"type": "string", "minLength": 1, "maxLength": 6000}}, ["question", "answer"]), _evaluate_answer),
        ToolDefinition("evaluate_salary", "按城市、经验和技能数量给出规则估算薪资区间。", _object({"city": {"type": "string", "maxLength": 20}, "experience": {"type": "string", "enum": ["应届生", "1-3年", "3-5年", "5年以上"]}, "skills_count": {"type": "integer"}}), _evaluate_salary),
        ToolDefinition("list_applications", "读取当前用户的投递记录。", _object(), _list_applications),
        ToolDefinition("get_dashboard", "读取当前用户简历、匹配、面试和投递统计。", _object(), _dashboard),
        ToolDefinition("generate_career_report", "汇总当前用户求职数据形成阶段报告素材。", _object(), _career_report),
        ToolDefinition("web_search", "搜索需要时效性的公开互联网信息。", _object({"query": {"type": "string", "minLength": 2, "maxLength": 200}}, ["query"]), _web_search),
        ToolDefinition("fetch_webpage", "读取指定公开网页的文本内容。", _object({"url": {"type": "string", "minLength": 8, "maxLength": 2000}}, ["url"]), _fetch_webpage),
    ]
    for definition in definitions:
        registry.register(definition)
    return registry

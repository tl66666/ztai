from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import math
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
from utils.agent_runtime.resume_draft import local_resume_diagnosis, local_resume_draft
from utils.agent_runtime.actions import (
    PROPOSAL_STATUSES,
    ActionProposalService,
    career_action_tool_schema,
)
from utils.ai_client import extract_keywords
from utils.domain.career import ACTION_STATUSES, CareerService
from utils.domain.interviews import InterviewService


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
    return _validate_schema_value(schema, arguments, "参数", schema, 0, 0, None)


def _validate_schema_value(
    schema: dict,
    value,
    path: str,
    root_schema: dict,
    schema_depth: int,
    data_depth: int,
    max_data_depth: int | None,
) -> list[str]:
    if schema_depth > 100:
        return [f"{path} 结构过于复杂"]
    if "x-maxDataDepth" in schema:
        max_data_depth = int(schema["x-maxDataDepth"])
        data_depth = 0
    if max_data_depth is not None and data_depth > max_data_depth:
        return [f"{path} 嵌套过深"]
    if "$ref" in schema:
        target = _resolve_local_ref(root_schema, schema["$ref"])
        return _validate_schema_value(
            target, value, path, root_schema,
            schema_depth + 1, data_depth, max_data_depth,
        )

    errors: list[str] = []
    if "oneOf" in schema:
        matches = [
            branch
            for branch in schema["oneOf"]
            if not _validate_schema_value(
                branch, value, path, root_schema,
                schema_depth + 1, data_depth, max_data_depth,
            )
        ]
        if len(matches) != 1:
            errors.append(f"{path} 不符合允许结构")
            return errors

    if "const" in schema and value != schema["const"]:
        return [f"{path} 必须为 {schema['const']}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path} 不在允许范围"]

    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_matches_schema_type(item, value) for item in expected_types):
            return [f"{path} 类型错误"]

    if isinstance(value, dict):
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path} 字段不足")
        if len(value) > schema.get("maxProperties", 1_000_000):
            errors.append(f"{path} 字段过多")
        properties = schema.get("properties", {})
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for key in value:
                errors.extend(
                    _validate_schema_value(
                        property_names, key, f"{path} 字段名", root_schema,
                        schema_depth + 1, data_depth, max_data_depth,
                    )
                )
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"缺少参数 {path}.{key}")
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(
                    _validate_schema_value(
                        properties[key], item, child_path, root_schema,
                        schema_depth + 1, data_depth + 1, max_data_depth,
                    )
                )
            elif additional is False:
                errors.append(f"不支持参数 {child_path}")
            elif isinstance(additional, dict):
                errors.extend(
                    _validate_schema_value(
                        additional, item, child_path, root_schema,
                        schema_depth + 1, data_depth + 1, max_data_depth,
                    )
                )
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path} 项目不足")
        if len(value) > schema.get("maxItems", 1_000_000):
            errors.append(f"{path} 项目过多")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _validate_schema_value(
                        item_schema,
                        item,
                        f"{path}[{index}]",
                        root_schema,
                        schema_depth + 1,
                        data_depth + 1,
                        max_data_depth,
                    )
                )
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path} 太短")
        if len(value) > schema.get("maxLength", 1_000_000):
            errors.append(f"{path} 太长")
        pattern = schema.get("pattern")
        if pattern and not re.fullmatch(pattern, value):
            errors.append(f"{path} 格式错误")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path} 必须是有限数字")
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} 过小")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} 过大")
    return errors


def _resolve_local_ref(root_schema: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        return {}
    current = root_schema
    for part in reference[2:].split("/"):
        current = current.get(part, {}) if isinstance(current, dict) else {}
    return current if isinstance(current, dict) else {}


def _matches_schema_type(expected: str, value) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True


class ToolRegistry:
    def __init__(self, db_path: str, local_user_id: int = 1):
        self.db_path = db_path
        self.local_user_id = int(local_user_id)
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
                user_id=self.local_user_id,
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
        except LookupError:
            return ToolResult(False, display_text="未找到可读取的数据", error_code="not_found")
        except PermissionError:
            return ToolResult(False, display_text="无权读取该数据", error_code="forbidden")
        except (ValueError, TypeError):
            return ToolResult(False, display_text="工具参数无效", error_code="invalid_arguments", retryable=False)
        except sqlite3.Error:
            return ToolResult(False, display_text="数据读取失败", error_code="tool_error", retryable=False)
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
    analysis = local_resume_diagnosis(
        resume.data["content"], arguments.get("job_title", "")
    )
    return ToolResult(
        True,
        data={"resume_id": resume.data["id"], "analysis": analysis, "mode": "local"},
        display_text=analysis,
    )


def _prepare_resume_revision(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    profile = CareerService(context.db_path, local_user_id=context.user_id).get_profile(context.user_id) or {}
    target_role = str(arguments.get("target_job_title") or profile.get("target_role") or "").strip()
    draft = local_resume_draft(resume.data["content"], target_role)
    label = "Agent 优化版" if not target_role else f"{target_role} 优化版"
    metadata = {
        "version_label": label,
        "target_job_title": target_role,
        "status": "active",
        "source_type": "agent",
        "title": f"{resume.data['title']} · {label}",
    }
    data = {
        "resume_id": resume.data["id"],
        "content": draft.content,
        "metadata": metadata,
        "mode": draft.mode,
        "changes": list(draft.changes),
    }
    mode_label = "模型定向改写" if draft.mode == "model" else "本地事实保真草稿"
    return ToolResult(
        True,
        data=data,
        display_text=(
            f"已生成{mode_label}。" + "；".join(draft.changes)
            + "。请在预览中检查并编辑，再确认保存为新版本。"
        ),
    )


def _diagnose_resume(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    profile = CareerService(context.db_path, local_user_id=context.user_id).get_profile(context.user_id) or {}
    target_role = str(arguments.get("job_title") or profile.get("target_role") or "").strip()
    analysis = local_resume_diagnosis(resume.data["content"], target_role)
    return ToolResult(
        True,
        data={"resume_id": resume.data["id"], "analysis": analysis, "mode": "local"},
        display_text=analysis,
    )


def _match_job(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    job_title = str(arguments["job_title"] or "").strip()
    job_text = f"{job_title}\n{str(arguments.get('jd') or '').strip()}"
    resume_keywords = set(extract_keywords(resume.data["content"]))
    job_keywords = list(dict.fromkeys(extract_keywords(job_text)))
    matched = [item for item in job_keywords if item in resume_keywords]
    missing = [item for item in job_keywords if item not in resume_keywords]
    score = max(35, min(92, 55 + len(matched) * 8 - len(missing) * 3))
    analysis = (
        "本地岗位匹配（无需等待模型）\n"
        f"目标岗位：{job_title}\n"
        f"匹配度：{score} 分\n"
        f"已命中：{'、'.join(matched[:8]) or '暂未识别到直接命中关键词'}\n"
        f"待补强：{'、'.join(missing[:8]) or '当前关键词覆盖较完整'}\n"
        "下一步：将待补强词放入真实项目职责或成果中，再结合具体 JD 完成针对性改写。"
    )
    return ToolResult(
        True,
        data={
            "resume_id": resume.data["id"], "score": score,
            "matched_keywords": matched, "missing_keywords": missing,
            "analysis": analysis, "mode": "local",
        },
        display_text=analysis,
    )


def _analyze_jd(arguments: dict, context: ToolContext) -> ToolResult:
    jd = str(arguments["jd_text"] or "").strip()
    keywords = list(dict.fromkeys(extract_keywords(jd)))
    clauses = [item.strip() for item in jd.replace("\n", "。 ").split("。") if item.strip()]
    focus = "；".join(clauses[:3])[:360] or "请补充岗位职责和任职要求。"
    analysis = (
        "本地 JD 要点（无需等待模型）\n"
        f"核心关键词：{'、'.join(keywords[:10]) or '暂未识别，请补充更完整 JD'}\n"
        f"职责摘录：{focus}\n"
        "准备建议：优先用项目中的真实动作、工具和结果证明上述关键词，再准备一个对应的面试案例。"
    )
    return ToolResult(True, data={"keywords": keywords, "analysis": analysis, "mode": "local"}, display_text=analysis)


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


_APPLICATION_SUMMARY_FIELDS = (
    "id", "company", "job_title", "status", "city", "updated_at",
)
_OPPORTUNITY_DETAIL_FIELDS = (
    *_APPLICATION_SUMMARY_FIELDS,
    "channel", "resume_id", "priority", "next_action_at", "interview_at",
    "deadline_at", "applied_at", "created_at", "needs_status_review",
)


def _project_fields(value: dict, fields: tuple[str, ...]) -> dict:
    return {field: value.get(field) for field in fields if field in value}


def _list_applications(arguments: dict, context: ToolContext) -> ToolResult:
    rows = CareerService(context.db_path, context.user_id).list_opportunities(context.user_id)
    data = [_project_fields(row, _APPLICATION_SUMMARY_FIELDS) for row in rows]
    text = "\n".join(f"{row['company']} / {row['job_title']} / {row['status']}" for row in data)
    return ToolResult(True, data=data, display_text=text or "暂无投递记录")


def _dashboard(arguments: dict, context: ToolContext) -> ToolResult:
    service = CareerService(context.db_path, context.user_id)
    data = service.agent_dashboard_summary(context.user_id)
    readiness = data["readiness"]
    text = (
        f"简历={data['resumes']}；匹配={data['matches']}；面试={data['interviews']}；"
        f"投递={data['applications']}；求职准备度={readiness['score']}（{readiness['label']}）"
    )
    return ToolResult(True, data=data, display_text=text)


def _career_report(arguments: dict, context: ToolContext) -> ToolResult:
    dashboard = _dashboard({}, context)
    applications = _list_applications({}, context)
    data = {"dashboard": dashboard.data, "applications": applications.data}
    readiness = dashboard.data["readiness"]
    recent = "\n".join(
        f"{item['company']} / {item['job_title']} / {item['status']}"
        for item in applications.data[:8]
    )
    text = (
        f"求职准备度：{readiness['score']}（{readiness['label']}）\n"
        f"最近投递：\n{recent or '暂无投递记录'}"
    )
    return ToolResult(True, data=data, display_text=text)


def _career_profile(arguments: dict, context: ToolContext) -> ToolResult:
    data = CareerService(context.db_path, context.user_id).get_profile(context.user_id)
    return ToolResult(
        True,
        data=data,
        display_text=json.dumps(data, ensure_ascii=False) if data else "暂无职业档案",
    )


def _opportunity(arguments: dict, context: ToolContext) -> ToolResult:
    try:
        row = CareerService(context.db_path, context.user_id).get_opportunity(
            context.user_id, arguments["opportunity_id"]
        )
    except LookupError:
        return ToolResult(False, display_text="未找到投递机会", error_code="not_found")
    data = _project_fields(row, _OPPORTUNITY_DETAIL_FIELDS)
    return ToolResult(
        True,
        data=data,
        display_text=f"{data['company']} / {data['job_title']} / {data['status']}",
    )


def _training_insights(arguments: dict, context: ToolContext) -> ToolResult:
    data = InterviewService(context.db_path, context.user_id).training_insights(
        context.user_id
    )
    return ToolResult(
        True,
        data=data,
        display_text=(
            f"最近完成训练：面试 {data['interviews']['completed_count']} 次，"
            f"题库 {data['practice']['completed_count']} 次，"
            f"语音 {data['audio']['completed_count']} 次"
        ),
    )


def _list_action_items(arguments: dict, context: ToolContext) -> ToolResult:
    status = arguments.get("status")
    data = CareerService(context.db_path, context.user_id).list_action_items(
        context.user_id
    )
    if status:
        data = [item for item in data if item.get("status") == status]
    text = "\n".join(f"#{item['id']} {item['title']} / {item['status']}" for item in data)
    return ToolResult(True, data=data, display_text=text or "暂无行动项")


def _list_agent_actions(arguments: dict, context: ToolContext) -> ToolResult:
    service = ActionProposalService(context.db_path, local_user_id=context.user_id)
    proposals = service.list_actions(context.user_id, arguments.get("status"))
    data = [service.public(item) for item in proposals]
    text = "\n".join(f"#{item['id']} {item['preview']} / {item['status']}" for item in data)
    return ToolResult(True, data=data, display_text=text or "暂无操作提案")


def _propose_career_action(arguments: dict, context: ToolContext) -> ToolResult:
    service = ActionProposalService(context.db_path, local_user_id=context.user_id)
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
        ToolDefinition("analyze_resume", "基于简历正文执行即时、本地优先的质量诊断，不等待第二次模型调用。", _object({"resume_id": {"type": "integer"}, "job_title": {"type": "string", "maxLength": 80}}), _analyze_resume),
        ToolDefinition("diagnose_resume", "对指定简历执行本地优先诊断；无模型密钥也会检查结构、证据和岗位对齐。", _object({"resume_id": {"type": "integer", "minimum": 1}, "job_title": {"type": "string", "maxLength": 80}}, ["resume_id"]), _diagnose_resume),
        ToolDefinition("prepare_resume_revision", "基于原始事实即时生成可编辑的新版本草稿；只生成待确认内容，不保存。", _object({"resume_id": {"type": "integer", "minimum": 1}, "target_job_title": {"type": "string", "maxLength": 80}}, ["resume_id"]), _prepare_resume_revision),
        ToolDefinition("match_job", "基于简历和 JD 关键词即时生成可解释的岗位匹配素材。", _object({"resume_id": {"type": "integer"}, "job_title": {"type": "string", "minLength": 2, "maxLength": 80}, "jd": {"type": "string", "maxLength": 8000}}, ["job_title"]), _match_job),
        ToolDefinition("analyze_jd", "即时提取岗位 JD 的关键词、职责摘录和准备方向。", _object({"jd_text": {"type": "string", "minLength": 10, "maxLength": 10000}}, ["jd_text"]), _analyze_jd),
        ToolDefinition("get_interview_question", "获取指定方向的一道面试题。", _object({"category": {"type": "string", "maxLength": 30}}), _interview_question),
        ToolDefinition("evaluate_answer", "评估用户的面试回答。", _object({"question": {"type": "string", "minLength": 2, "maxLength": 1000}, "answer": {"type": "string", "minLength": 1, "maxLength": 6000}}, ["question", "answer"]), _evaluate_answer),
        ToolDefinition("evaluate_salary", "按城市、经验和技能数量给出规则估算薪资区间。", _object({"city": {"type": "string", "maxLength": 20}, "experience": {"type": "string", "enum": ["应届生", "1-3年", "3-5年", "5年以上"]}, "skills_count": {"type": "integer"}}), _evaluate_salary),
        ToolDefinition("list_applications", "读取当前用户的投递记录。", _object(), _list_applications),
        ToolDefinition("get_dashboard", "读取当前用户简历、匹配、面试和投递统计。", _object(), _dashboard),
        ToolDefinition("generate_career_report", "汇总当前用户求职数据形成阶段报告素材。", _object(), _career_report),
        ToolDefinition("get_career_profile", "读取当前用户已确认的职业档案。", _object(), _career_profile),
        ToolDefinition("get_opportunity", "读取当前用户指定的未删除投递机会。", _object({"opportunity_id": {"type": "integer"}}, ["opportunity_id"]), _opportunity),
        ToolDefinition("get_training_insights", "汇总最近完成的面试、题库和语音训练质量，不返回回答、反馈全文或音频内容。", _object(), _training_insights),
        ToolDefinition("list_action_items", "读取当前用户行动项，可按状态筛选。", _object({"status": {"type": "string", "enum": list(ACTION_STATUSES)}}), _list_action_items),
        ToolDefinition("list_agent_actions", "读取当前用户的操作提案，只返回脱敏公开字段。", _object({"status": {"type": "string", "enum": sorted(PROPOSAL_STATUSES)}}), _list_agent_actions),
        ToolDefinition(
            "propose_career_action",
            "创建待用户在界面确认的职业操作提案；本工具不会执行、确认或取消操作。",
            career_action_tool_schema(),
            _propose_career_action,
            read_only=False,
        ),
        ToolDefinition("web_search", "搜索需要时效性的公开互联网信息。", _object({"query": {"type": "string", "minLength": 2, "maxLength": 200}}, ["query"]), _web_search),
        ToolDefinition("fetch_webpage", "读取指定公开网页的文本内容。", _object({"url": {"type": "string", "minLength": 8, "maxLength": 2000}}, ["url"]), _fetch_webpage),
    ]
    for definition in definitions:
        registry.register(definition)
    return registry

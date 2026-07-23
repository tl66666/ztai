from __future__ import annotations

import json
import random

from utils.agent_runtime.models import ToolResult
from utils.agent_runtime.resume_draft import (
    local_resume_diagnosis,
    local_resume_draft,
    model_resume_draft,
)
from utils.ai_client import extract_keywords

from .tool_registry import ToolContext


def _list_resumes(arguments: dict, context: ToolContext) -> ToolResult:
    rows = context.persistence.list_resumes(context.user_id)
    data = [dict(row) for row in rows]
    text = "\n".join(f"#{row['id']} {row['title']}：{row['preview']}" for row in data)
    return ToolResult(True, data=data, display_text=text or "暂无已保存简历")


def _get_resume(arguments: dict, context: ToolContext) -> ToolResult:
    resume_id = arguments.get("resume_id")
    row = context.persistence.get_resume(context.user_id, resume_id)
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
    analysis = local_resume_diagnosis(resume.data["content"], arguments.get("job_title", ""))
    return ToolResult(
        True,
        data={"resume_id": resume.data["id"], "analysis": analysis, "mode": "local"},
        display_text=analysis,
    )


def _prepare_resume_revision(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    profile = context.career_service.get_profile(context.user_id) or {}
    target_role = str(arguments.get("target_job_title") or profile.get("target_role") or "").strip()
    client = context.ai_client_provider()
    draft = (
        model_resume_draft(
            client,
            resume.data["content"],
            target_role,
            timeout=context.request_timeout(32),
        )
        if getattr(client, "api_key", "")
        else local_resume_draft(resume.data["content"], target_role)
    )
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
            f"已生成{mode_label}。"
            + "；".join(draft.changes)
            + "。请在预览中检查并编辑，再确认保存为新版本。"
        ),
    )


def _diagnose_resume(arguments: dict, context: ToolContext) -> ToolResult:
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    profile = context.career_service.get_profile(context.user_id) or {}
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
            "resume_id": resume.data["id"],
            "score": score,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "analysis": analysis,
            "mode": "local",
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
    return ToolResult(
        True,
        data={"keywords": keywords, "analysis": analysis, "mode": "local"},
        display_text=analysis,
    )


def _interview_question(arguments: dict, context: ToolContext) -> ToolResult:
    from config import INTERVIEW_QUESTIONS

    category = arguments.get("category", "general")
    questions = INTERVIEW_QUESTIONS.get(category) or INTERVIEW_QUESTIONS.get("general", [])
    if not questions:
        return ToolResult(False, display_text="暂无对应面试题", error_code="not_found")
    question = random.choice(questions)
    data = question if isinstance(question, dict) else {"question": str(question)}
    return ToolResult(True, data=data, display_text=data.get("question", ""))


def _resume_interview_questions(arguments: dict, context: ToolContext) -> ToolResult:
    """Generate a useful local question set without exposing the resume body."""
    resume = _owned_resume(arguments, context)
    if not resume.ok:
        return resume
    keywords = list(dict.fromkeys(extract_keywords(resume.data["content"])))
    primary = keywords[0] if keywords else "核心项目"
    secondary = keywords[1] if len(keywords) > 1 else "相关技术和流程"
    tertiary = keywords[2] if len(keywords) > 2 else "实现细节"
    title = str(resume.data.get("title") or "所选简历")[:80]
    questions = [
        f"请选一个与 {primary} 相关的经历，按背景、任务、行动、结果的顺序完整说明。",
        f"在涉及 {secondary} 的工作中，你具体负责什么？如何验证自己的方案有效？",
        f"围绕 {tertiary}，请讲一个你遇到问题、定位原因并推动解决的案例。",
        "如果面试官追问你的贡献与团队其他成员有什么不同，你会如何用事实和结果说明？",
        "结合这份简历的目标方向，入职后三个月你会优先补齐哪些能力，为什么？",
    ]
    text = (
        f"已根据《{title}》生成 5 道定制面试题（本地生成，无需 API Key）：\n"
        + "\n".join(f"{index}. {question}" for index, question in enumerate(questions, 1))
        + "\n\n建议逐题用 STAR 结构作答：先交代场景和任务，再说明你的行动与结果。"
    )
    return ToolResult(
        True,
        data={
            "resume_id": resume.data["id"],
            "questions": questions,
            "text": text,
            "mode": "local",
        },
        display_text=text,
    )


def _evaluate_answer(arguments: dict, context: ToolContext) -> ToolResult:
    from utils.interview_engine import InterviewEngine

    engine = InterviewEngine()
    engine.candidate_answers = [arguments["answer"]]
    result = engine.evaluate()
    return ToolResult(
        True, data=result, display_text=f"评分：{result['score']}分\n{result['feedback']}"
    )


def _evaluate_salary(arguments: dict, context: ToolContext) -> ToolResult:
    city = arguments.get("city", "")
    experience = arguments.get("experience", "应届生")
    skills_count = arguments.get("skills_count", 0)
    factor = {"北京": 1.25, "上海": 1.25, "深圳": 1.2, "广州": 1.05, "杭州": 1.15, "成都": 0.9}.get(
        city, 1
    )
    base = {"应届生": 9000, "1-3年": 15000, "3-5年": 24000, "5年以上": 36000}.get(experience, 12000)
    average = int((base + min(5000, skills_count * 500)) * factor)
    data = {
        "city": city,
        "experience": experience,
        "minimum": int(average * 0.75),
        "maximum": int(average * 1.35),
        "average": average,
        "estimate_only": True,
    }
    return ToolResult(
        True,
        data=data,
        display_text=f"规则估算：{data['minimum']}-{data['maximum']} 元/月（非实时行情）",
    )


_APPLICATION_SUMMARY_FIELDS = (
    "id",
    "company",
    "job_title",
    "status",
    "city",
    "updated_at",
)
_OPPORTUNITY_DETAIL_FIELDS = (
    *_APPLICATION_SUMMARY_FIELDS,
    "channel",
    "resume_id",
    "priority",
    "next_action_at",
    "interview_at",
    "deadline_at",
    "applied_at",
    "created_at",
    "needs_status_review",
)


def _project_fields(value: dict, fields: tuple[str, ...]) -> dict:
    return {field: value.get(field) for field in fields if field in value}


def _list_applications(arguments: dict, context: ToolContext) -> ToolResult:
    rows = context.career_service.list_opportunities(context.user_id)
    data = [_project_fields(row, _APPLICATION_SUMMARY_FIELDS) for row in rows]
    text = "\n".join(f"{row['company']} / {row['job_title']} / {row['status']}" for row in data)
    return ToolResult(True, data=data, display_text=text or "暂无投递记录")


def _dashboard(arguments: dict, context: ToolContext) -> ToolResult:
    service = context.career_service
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
    data = context.career_service.get_profile(context.user_id)
    return ToolResult(
        True,
        data=data,
        display_text=json.dumps(data, ensure_ascii=False) if data else "暂无职业档案",
    )


def _opportunity(arguments: dict, context: ToolContext) -> ToolResult:
    try:
        row = context.career_service.get_opportunity(context.user_id, arguments["opportunity_id"])
    except LookupError:
        return ToolResult(False, display_text="未找到投递机会", error_code="not_found")
    data = _project_fields(row, _OPPORTUNITY_DETAIL_FIELDS)
    return ToolResult(
        True,
        data=data,
        display_text=f"{data['company']} / {data['job_title']} / {data['status']}",
    )


def _training_insights(arguments: dict, context: ToolContext) -> ToolResult:
    data = context.interview_service.training_insights(context.user_id)
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
    data = context.career_service.list_action_items(context.user_id)
    if status:
        data = [item for item in data if item.get("status") == status]
    text = "\n".join(f"#{item['id']} {item['title']} / {item['status']}" for item in data)
    return ToolResult(True, data=data, display_text=text or "暂无行动项")

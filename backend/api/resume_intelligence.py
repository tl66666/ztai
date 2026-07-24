from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.http import domain_error_response, json_object_body
from backend.application.resume_intelligence import ResumeIntelligenceModule


def create_resume_intelligence_router(
    module_provider: Callable[[], ResumeIntelligenceModule],
) -> APIRouter:
    router = APIRouter(tags=["resume-intelligence"])

    async def body(request: Request) -> dict[str, Any]:
        return await json_object_body(request)

    async def invoke(method: str, *args: Any) -> JSONResponse:
        try:
            payload, status_code = await run_in_threadpool(
                getattr(module_provider(), method), *args
            )
            return JSONResponse(payload, status_code=status_code)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.post("/api/resumes/{resume_id}/analyze")
    async def analyze(resume_id: int, request: Request):
        return await invoke("analyze", resume_id, await body(request))

    @router.post("/api/resumes/{resume_id}/audit")
    async def audit(resume_id: int, request: Request):
        return await invoke("audit", resume_id, await body(request))

    @router.post("/api/resumes/{resume_id}/improve")
    async def improve(resume_id: int, request: Request):
        return await invoke("improve", resume_id, await body(request))

    @router.post("/api/resumes/{resume_id}/optimize")
    async def optimize(resume_id: int, request: Request):
        return await invoke("optimize", resume_id, await body(request))

    @router.post("/api/resumes/{resume_id}/tailor")
    async def tailor(resume_id: int, request: Request):
        return await invoke("tailor", resume_id, await body(request))

    @router.post("/api/job-match")
    async def job_match(request: Request):
        return await invoke("job_match", await body(request))

    @router.post("/api/skills/radar")
    async def skills_radar(request: Request):
        try:
            payload = await run_in_threadpool(module_provider().skills_radar, await body(request))
            return JSONResponse(payload)
        except (PermissionError, LookupError, ValueError) as exc:
            return domain_error_response(exc)

    @router.post("/api/resume-generator")
    async def resume_generator(request: Request):
        data = await body(request)
        name = data.get("name", "候选人")
        target = data.get("job_target", "目标岗位")
        skills = data.get("skills", "Python, Flask, Selenium, JMeter")
        content = f"""{name}
求职意向：{target}

核心技能：{skills}

项目经历：AI 求职辅助 Web 系统
- 负责系统需求梳理、功能实现与测试验证，覆盖简历管理、JD 匹配、模拟面试、求职进度看板。
- 设计接口测试、功能测试和性能测试用例，输出测试报告与缺陷记录。
- 通过多模型 API 接入和本地兜底策略，提高 AI 功能可用性。

自我评价：学习能力强，能把课程实训、真实求职场景和工程实现结合起来，重视可用性与测试闭环。
"""
        return JSONResponse({"success": True, "resume_content": content})

    @router.post("/api/ai/analyze-jd")
    async def analyze_jd(request: Request):
        payload = await run_in_threadpool(module_provider().analyze_jd, await body(request))
        return JSONResponse(payload)

    @router.post("/api/ai/compare-jds")
    async def compare_jds(request: Request):
        payload = await run_in_threadpool(module_provider().compare_jds, await body(request))
        return JSONResponse(payload)

    @router.get("/api/resume-templates")
    async def resume_templates():
        return {
            "success": True,
            "data": {
                "campus_test": {
                    "name": "应届测试工程师模板",
                    "description": "突出测试工具、课程项目、缺陷报告和自动化意识。",
                    "sections": [
                        "个人信息",
                        "求职意向",
                        "核心技能",
                        "项目经历",
                        "测试实践",
                        "教育背景",
                    ],
                    "tips": ["每个项目写清测试对象", "补充工具和指标", "保留实训报告作为证据"],
                },
                "ai_product": {
                    "name": "AI 应用项目模板",
                    "description": "适合把本系统包装成 AI Agent 项目经历。",
                    "sections": [
                        "项目背景",
                        "技术架构",
                        "智能体能力",
                        "模型接入",
                        "测试验证",
                        "项目成果",
                    ],
                    "tips": ["强调多模型路由", "强调兜底策略", "强调真实求职流程"],
                },
            },
        }

    return router

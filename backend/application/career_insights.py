from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from backend.ports.persistence import UnitOfWorkFactory
from utils.domain.opportunity_coaching import build_followup_plan


class CareerInsightsModule:
    """Own read models and coaching derived from career evidence."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        career_service: Any,
        ai_client_provider: Callable[[], Any],
        *,
        local_user_id: int,
    ):
        self._unit_of_work = unit_of_work
        self._career_service = career_service
        self._ai_client_provider = ai_client_provider
        self._local_user_id = int(local_user_id)

    def dashboard(self, requested_user_id: int) -> dict[str, Any]:
        self._require_local_user(requested_user_id)
        with self._unit_of_work() as unit_of_work:
            evidence = unit_of_work.career_insights.dashboard_evidence(
                self._local_user_id
            )
        interviews = evidence["interviews"]
        matches = evidence["matches"]
        applications = evidence["applications"]
        stats = {
            "resumes": evidence["resume_count"],
            "interviews": len(interviews),
            "matches": len(matches),
            "applications": len(applications),
            "practices": evidence["practice_count"],
            "audios": evidence["audio_count"],
        }
        return {
            "success": True,
            "stats": stats,
            "interview_scores": [dict(row) for row in interviews],
            "match_scores": [dict(row) for row in matches],
            "activities": [dict(row) for row in applications[:6]],
            "next_actions": self._next_actions(stats),
            "career_pulse": self._career_service.calculate_readiness(self._local_user_id),
        }

    def report(self, requested_user_id: int) -> dict[str, Any]:
        self._require_local_user(requested_user_id)
        with self._unit_of_work() as unit_of_work:
            evidence = unit_of_work.career_insights.report_evidence(
                self._local_user_id
            )
        report = self._local_report(
            evidence["resumes"],
            evidence["matches"],
            evidence["interviews"],
            evidence["applications"],
        )
        client = self._ai_client_provider()
        if client.api_key:
            result = client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是求职策略教练。请把用户当前求职数据整理成"
                            "一份结构清晰、行动明确的中文作战报告。"
                        ),
                    },
                    {"role": "user", "content": report},
                ],
                temperature=0.35,
                max_tokens=1100,
            )
            if result.get("success"):
                report = result["content"]
        return {"success": True, "report": report}

    def coach(self, application_id: int) -> dict[str, Any]:
        application = self._career_service.get_opportunity(self._local_user_id, application_id)
        with self._unit_of_work() as unit_of_work:
            evidence = unit_of_work.career_insights.coaching_evidence(
                self._local_user_id
            )
        resume = evidence["resume"]
        interview = evidence["interview"]
        plan = build_followup_plan(application, resume, interview)
        ai_note = ""
        client = self._ai_client_provider()
        if client.api_key:
            result = client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是求职投递教练。请根据投递阶段给出简洁、可执行的跟进建议，不要空话。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "application": dict(application),
                                "latest_resume": (dict(resume) if resume else None),
                                "latest_interview": (dict(interview) if interview else None),
                                "local_plan": plan,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.35,
                max_tokens=700,
            )
            if result.get("success"):
                ai_note = result.get("content", "")
        return {"success": True, **plan, "ai_note": ai_note}

    def _require_local_user(self, requested_user_id: int) -> None:
        if int(requested_user_id) != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")

    @staticmethod
    def _local_report(
        resumes: list[Any],
        matches: list[Any],
        interviews: list[Any],
        applications: list[Any],
    ) -> str:
        resume_line = "暂无简历，第一优先级是录入一份可分析简历。"
        if resumes:
            resume_line = "已保存简历：" + "、".join(row["title"] for row in resumes)
        match_line = "暂无 JD 匹配记录，建议先选 1 个真实岗位做定制优化。"
        if matches:
            average = round(sum(row["match_score"] or 0 for row in matches) / len(matches))
            match_line = (
                f"最近 {len(matches)} 次 JD 匹配平均分约 {average}，重点看低分岗位的关键词缺口。"
            )
        interview_line = "暂无模拟面试记录，建议先跑一轮完整流程。"
        if interviews:
            average = round(sum(row["score"] or 0 for row in interviews) / len(interviews))
            interview_line = (
                f"最近 {len(interviews)} 次面试训练平均分约 {average}，"
                "建议继续打磨自我介绍和项目深挖。"
            )
        application_line = "暂无投递记录，建议建立投递看板，避免只投不跟进。"
        if applications:
            counts: dict[str, int] = {}
            for row in applications:
                counts[row["status"]] = counts.get(row["status"], 0) + 1
            application_line = "当前投递阶段分布：" + "、".join(
                f"{key}{value}条" for key, value in counts.items()
            )
        return (
            "## 求职作战报告\n"
            f"### 1. 简历资产\n{resume_line}\n\n"
            f"### 2. 岗位匹配\n{match_line}\n\n"
            f"### 3. 面试训练\n{interview_line}\n\n"
            f"### 4. 投递推进\n{application_line}\n\n"
            "### 5. 下一步建议\n"
            "- 先选一个真实 JD 做简历定制，生成匹配分和缺口清单。\n"
            "- 把 JD 自动带入模拟面试，完成一轮完整流程。\n"
            "- 将目标公司加入投递看板，按阶段推进并生成跟进话术。\n"
            "- 把最终优化后的项目经历导出为 PDF/Word，用于真实投递。"
        )

    @staticmethod
    def _next_actions(stats: dict[str, int]) -> list[dict[str, str]]:
        actions = []
        if stats["resumes"] == 0:
            actions.append(
                {
                    "title": "先建立一份可分析的简历",
                    "description": (
                        "上传 Word/PDF 或粘贴文本，系统才能做诊断、JD 匹配、导出和面试追问。"
                    ),
                    "page": "resume",
                    "module": "input",
                    "cta": "录入简历",
                }
            )
        else:
            actions.append(
                {
                    "title": "用 JD 检查简历是否命中岗位",
                    "description": (
                        "把目标岗位 JD 粘进去，系统会给出匹配分、关键词缺口和可讲述的项目亮点。"
                    ),
                    "page": "resume",
                    "module": "jd",
                    "cta": "做 JD 优化",
                }
            )
        if stats["interviews"] == 0:
            actions.append(
                {
                    "title": "跑一轮完整模拟面试",
                    "description": (
                        "从自我介绍、项目深挖到反问总结，训练结果会沉淀到 AI 教练上下文。"
                    ),
                    "page": "interview",
                    "module": "mock",
                    "cta": "开始面试",
                }
            )
        if stats["applications"] == 0:
            actions.append(
                {
                    "title": "建立投递看板",
                    "description": ("记录公司、岗位、阶段和备注，后续可以生成跟进话术和谈薪准备。"),
                    "page": "tracker",
                    "module": "add",
                    "cta": "新增投递",
                }
            )
        else:
            actions.append(
                {
                    "title": "推进投递状态并复盘反馈",
                    "description": (
                        "把投递从已投递推进到笔试/面试/Offer，系统会按阶段给跟进建议。"
                    ),
                    "page": "tracker",
                    "module": "board",
                    "cta": "看投递板",
                }
            )
        return actions[:3]

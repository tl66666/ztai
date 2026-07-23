from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_STAGE_RULES = {
    "已投递": (
        "投递后 2-3 天检查岗位状态；如果没有反馈，补充一次礼貌跟进，"
        "并同步准备该岗位的 2 分钟项目介绍。",
        "风险是只投不跟进，后续忘记岗位要求；建议在备注里补充投递渠道、"
        "JD 关键词和截止时间。",
    ),
    "简历筛选": (
        "围绕 JD 关键词再做一次简历定制，准备一版更贴合该岗位的项目经历表述。",
        "风险是简历泛化，HR 看不到岗位相关证据；需要把工具、动作、结果写进项目经历。",
    ),
    "笔试": (
        "整理笔试范围，优先准备基础题、接口测试、SQL、Python/前端基础和项目场景题。",
        "风险是只刷题不复盘；建议记录错题类型，并把知识点转成面试可讲案例。",
    ),
    "一面": (
        "准备自我介绍、项目深挖、技术追问和反问问题；用模拟面试模块跑一轮完整流程。",
        "风险是项目讲得像流水账；建议用 STAR 结构讲清背景、动作、结果和个人贡献。",
    ),
    "二面": (
        "强化项目决策、问题定位、协作推动和结果量化，准备 2 个能体现成长性的案例。",
        "风险是回答停留在功能层；需要补充为什么这样设计、如何验证、遇到问题怎么取舍。",
    ),
    "HR 面": (
        "准备求职动机、稳定性、薪资预期和到岗时间；提前查城市和岗位薪资区间。",
        "风险是薪资表达没依据；建议用城市、经验、技能匹配度和 Offer 进度作为谈薪支撑。",
    ),
    "Offer": (
        "核对薪资结构、试用期、五险一金、工作地点、入职材料和违约条款，再做最终选择。",
        "风险是只看月薪不看总包和试用期规则；建议整理对比表后再确认。",
    ),
    "已拒绝": (
        "记录拒绝原因，把它转成简历、面试或技能的下一轮改进项。",
        "风险是只记录失败结果，不沉淀原因；建议复盘筛选、笔试、面试各阶段卡点。",
    ),
}


def build_followup_plan(
    opportunity: Mapping[str, Any],
    resume: Mapping[str, Any] | None,
    interview: Mapping[str, Any] | None,
) -> dict[str, Any]:
    company = opportunity["company"]
    job = opportunity["job_title"]
    status = opportunity["status"]
    city = opportunity["city"] or "目标城市"
    notes = opportunity["notes"] or ""
    resume_hint = f"最近简历《{resume['title']}》" if resume else "当前暂无已保存简历"
    interview_hint = ""
    if interview:
        interview_hint = (
            f"最近一次 {interview['job_title']} 模拟面试得分 {interview['score']}，"
            "建议把低分维度转成复盘待办。"
        )

    next_action, risk = _STAGE_RULES.get(status, _STAGE_RULES["已投递"])
    if notes:
        risk += f" 当前备注里已有线索：{notes[:120]}"
    template = (
        f"您好，我是投递 {company}「{job}」岗位的候选人。想礼貌确认一下目前"
        f"流程进展。我这边可以结合岗位要求补充 {resume_hint} 中与岗位更相关的"
        "项目材料，也可以配合后续笔试/面试安排。谢谢。"
    )
    if status in {"一面", "二面", "HR 面"}:
        template = (
            f"您好，感谢之前关于 {company}「{job}」岗位的沟通。"
            "我已根据面试反馈继续梳理项目经历和岗位匹配点，想确认一下后续"
            "流程安排。谢谢。"
        )
    return {
        "title": f"{company} / {job} 跟进策略",
        "company": company,
        "job_title": job,
        "status": status,
        "city": city,
        "next_action": next_action,
        "risk": risk,
        "message_template": template,
        "resume_hint": resume_hint,
        "interview_hint": interview_hint,
    }

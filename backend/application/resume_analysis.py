from __future__ import annotations

import re
from typing import Any

from utils.ai_client import extract_keywords

CAREER_PROFILES: dict[str, dict[str, Any]] = {
    "tech": {
        "label": "计算机 / 软件 / AI",
        "interviewer": "技术面试官",
        "keywords": [
            "软件",
            "测试",
            "Python",
            "Java",
            "前端",
            "后端",
            "算法",
            "AI",
            "数据",
            "接口",
            "自动化",
        ],
        "abilities": {
            "编程与工具": ["Python", "Java", "JavaScript", "SQL", "Git", "Linux"],
            "工程实践": ["接口", "测试", "自动化", "部署", "数据库", "性能"],
            "项目表达": ["项目", "需求", "方案", "结果", "复盘", "文档"],
            "AI 应用": ["AI", "大模型", "Prompt", "智能体", "模型", "数据"],
            "协作推进": ["沟通", "协作", "推进", "排查", "总结", "交付"],
        },
    },
    "ops": {
        "label": "运营 / 新媒体 / 内容",
        "interviewer": "运营主管",
        "keywords": [
            "运营",
            "新媒体",
            "内容",
            "用户",
            "社群",
            "活动",
            "转化",
            "增长",
            "公众号",
            "短视频",
        ],
        "abilities": {
            "内容策划": ["选题", "文案", "脚本", "排版", "热点", "账号"],
            "用户运营": ["用户", "社群", "留存", "转化", "私域", "增长"],
            "活动执行": ["活动", "预算", "流程", "复盘", "报名", "转化"],
            "数据复盘": ["数据", "PV", "UV", "点击", "转化率", "复盘"],
            "跨部门协作": ["沟通", "协调", "推进", "资源", "反馈", "落地"],
        },
    },
    "marketing": {
        "label": "市场 / 销售 / 商务",
        "interviewer": "市场负责人",
        "keywords": [
            "市场",
            "销售",
            "商务",
            "客户",
            "渠道",
            "品牌",
            "竞品",
            "线索",
            "转化",
            "谈判",
        ],
        "abilities": {
            "市场洞察": ["市场", "竞品", "用户画像", "行业", "调研", "定位"],
            "客户沟通": ["客户", "需求", "异议", "跟进", "谈判", "成交"],
            "渠道拓展": ["渠道", "BD", "合作", "资源", "线索", "转化"],
            "方案表达": ["方案", "PPT", "报价", "价值", "案例", "演示"],
            "结果复盘": ["业绩", "转化率", "复盘", "目标", "增长", "漏斗"],
        },
    },
    "finance": {
        "label": "财务 / 会计 / 审计",
        "interviewer": "财务经理",
        "keywords": [
            "财务",
            "会计",
            "审计",
            "税务",
            "报表",
            "凭证",
            "预算",
            "成本",
            "Excel",
            "金蝶",
            "用友",
        ],
        "abilities": {
            "会计基础": ["凭证", "分录", "科目", "账务", "结账", "对账"],
            "报表分析": ["资产负债表", "利润表", "现金流", "报表", "指标", "分析"],
            "税务合规": ["增值税", "所得税", "发票", "申报", "税务", "合规"],
            "工具效率": ["Excel", "透视表", "函数", "金蝶", "用友", "系统"],
            "风险意识": ["审计", "内控", "风险", "异常", "流程", "证据"],
        },
    },
    "education": {
        "label": "教育 / 师范 / 教培",
        "interviewer": "教研主管",
        "keywords": [
            "教育",
            "教师",
            "师范",
            "课程",
            "教案",
            "课堂",
            "学生",
            "家长",
            "教研",
            "班级",
        ],
        "abilities": {
            "教学设计": ["课程", "教案", "目标", "重难点", "活动", "评价"],
            "课堂表达": ["讲解", "互动", "板书", "提问", "反馈", "节奏"],
            "学生管理": ["学生", "班级", "纪律", "差异化", "激励", "沟通"],
            "教研反思": ["教研", "听评课", "反思", "改进", "案例", "复盘"],
            "家校沟通": ["家长", "沟通", "反馈", "记录", "协同", "问题"],
        },
    },
    "hr": {
        "label": "行政 / 人事 / 通用职能",
        "interviewer": "职能部门主管",
        "keywords": ["行政", "人事", "HR", "招聘", "员工", "流程", "制度", "档案", "培训", "组织"],
        "abilities": {
            "流程执行": ["流程", "制度", "审批", "归档", "规范", "执行"],
            "招聘支持": ["招聘", "筛选", "面试", "邀约", "入职", "候选人"],
            "沟通协调": ["沟通", "协调", "会议", "供应商", "跨部门", "反馈"],
            "数据记录": ["表格", "台账", "统计", "报表", "记录", "分析"],
            "服务意识": ["服务", "响应", "细致", "耐心", "问题", "跟进"],
        },
    },
}


def normalize_career_profile(value: str | None) -> str:
    key = (value or "").strip().lower()
    key = {
        "cs": "tech",
        "it": "tech",
        "software": "tech",
        "operation": "ops",
        "content": "ops",
        "sales": "marketing",
        "market": "marketing",
        "teacher": "education",
        "admin": "hr",
        "general": "hr",
    }.get(key, key)
    return key if key in CAREER_PROFILES else "tech"


def select_career_profile(
    data: dict[str, Any] | None = None,
    *,
    text: str = "",
    job_title: str = "",
) -> str:
    data = data or {}
    explicit = data.get("career_profile") or data.get("profile")
    if explicit:
        return normalize_career_profile(str(explicit))
    haystack = f"{job_title or data.get('job_title', '')}\n{text}".lower()
    scores = {
        key: sum(word.lower() in haystack for word in profile["keywords"])
        for key, profile in CAREER_PROFILES.items()
    }
    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    return best_key if best_score else "tech"


def score_resume_against_jd(
    resume_text: str,
    jd: str,
) -> tuple[int, list[str], list[str]]:
    resume_keywords = set(extract_keywords(resume_text))
    jd_keywords = set(extract_keywords(jd))
    if not jd_keywords:
        jd_keywords = {"项目", "沟通", "学习", "测试", "开发"}
    matched = sorted(resume_keywords & jd_keywords)
    missing = sorted(jd_keywords - resume_keywords)
    score = int(min(96, max(35, 50 + len(matched) * 8 - len(missing) * 3)))
    return score, matched, missing


def extract_jd_focus(jd: str) -> dict[str, list[str]]:
    focus_map = {
        "硬技能": [
            "Python",
            "Java",
            "Flask",
            "Vue",
            "React",
            "MySQL",
            "Redis",
            "Docker",
            "Selenium",
            "JMeter",
            "Postman",
            "Pytest",
        ],
        "测试能力": [
            "功能测试",
            "接口测试",
            "自动化测试",
            "性能测试",
            "测试用例",
            "缺陷",
            "回归测试",
        ],
        "AI 能力": ["AI", "智能体", "大模型", "Prompt", "模型", "算法"],
        "软技能": ["沟通", "协作", "推动", "学习", "文档", "总结"],
    }
    text = jd or ""
    return {
        name: [word for word in words if word.lower() in text.lower()]
        for name, words in focus_map.items()
    }


def career_jd_focus(jd: str, profile_key: str) -> dict[str, list[str]]:
    profile = CAREER_PROFILES[normalize_career_profile(profile_key)]
    return {
        name: [word for word in words if word.lower() in (jd or "").lower()]
        for name, words in profile["abilities"].items()
    }


def build_career_radar(text: str, profile_key: str) -> list[dict[str, Any]]:
    profile = CAREER_PROFILES[normalize_career_profile(profile_key)]
    lower_text = (text or "").lower()
    radar = []
    for name, words in profile["abilities"].items():
        matched = [word for word in words if word.lower() in lower_text]
        missing = [word for word in words if word not in matched][:4]
        score = min(10, 3 + len(matched) * 2)
        if score <= 5:
            suggestion = (
                f"建议补充{name}证据："
                f"{', '.join(missing) or '真实任务、工具、结果'}，"
                "写进经历而不是只放技能栏。"
            )
        elif score <= 7:
            suggestion = f"{name}基础可用，下一步补充量化结果、场景和个人贡献。"
        else:
            suggestion = f"{name}呈现较完整，建议保留最能贴合目标岗位的证据。"
        radar.append(
            {
                "category": name,
                "score": score,
                "matched": matched,
                "missing": missing,
                "suggestion": suggestion,
            }
        )
    return radar


def build_resume_audit(
    resume_text: str,
    job_title: str = "",
    jd: str = "",
) -> dict[str, Any]:
    text = resume_text or ""
    lower_text = text.lower()
    keywords = extract_keywords(text)
    score, matched, missing = score_resume_against_jd(text, jd or job_title)
    project_words = [
        "项目",
        "系统",
        "平台",
        "模块",
        "接口",
        "测试",
        "数据库",
        "前端",
        "后端",
        "模型",
        "智能体",
    ]
    tool_words = [
        "flask",
        "sqlite",
        "python",
        "javascript",
        "vue",
        "react",
        "mysql",
        "redis",
        "docker",
        "git",
        "postman",
        "jmeter",
        "selenium",
        "pytest",
    ]
    action_words = [
        "负责",
        "设计",
        "实现",
        "优化",
        "分析",
        "定位",
        "验证",
        "推动",
        "输出",
        "沉淀",
        "完成",
    ]
    result_words = [
        "提升",
        "降低",
        "覆盖",
        "发现",
        "修复",
        "通过",
        "稳定",
        "响应",
        "效率",
        "错误率",
        "缺陷",
        "结果",
    ]
    structure_words = ["背景", "目标", "职责", "行动", "结果", "产出", "复盘", "问题", "方案"]
    has_project = any(word in text for word in project_words)
    has_metrics = bool(re.search(r"\d+|%|次|条|个|ms|秒|分钟|小时|天|qps|接口|用例", text, re.I))
    matched_tools = [word for word in tool_words if word in lower_text]
    action_count = sum(text.count(word) for word in action_words)
    result_count = sum(text.count(word) for word in result_words)
    structure_count = sum(text.count(word) for word in structure_words)
    section_scores = {
        "岗位匹配": min(100, max(6, min(18, score // 5)) * 5) if jd else 50,
        "项目证据": min(
            100,
            (
                10
                + min(16, sum(text.count(word) for word in project_words) * 2)
                + 8
                + min(14, action_count * 3)
            )
            * 3,
        ),
        "量化结果": min(100, (8 + (14 if has_metrics else 0)) * 4),
        "工具链": min(100, (8 + min(14, len(matched_tools) * 3)) * 4),
        "表达结构": min(100, (8 + min(12, structure_count * 2) + min(18, len(text) // 80)) * 3),
    }
    risks: list[str] = []
    actions: list[str] = []
    brutal_comments: list[str] = []
    evidence_gaps: list[str] = []
    strengths: list[str] = []
    if len(text) < 500:
        risks.append("简历内容偏短，HR 很难判断项目深度和个人贡献。")
        actions.append("补充 1-2 个项目经历，每个项目写清背景、职责、技术/工具、结果。")
        brutal_comments.append("目前更像“我学过什么”的说明，不像“我解决过什么问题”的简历。")
        evidence_gaps.append("缺少足够的项目上下文：业务背景、负责模块、输入输出和结果都需要补。")
    if not has_project:
        risks.append("项目经历证据不足，像技能清单而不是可验证经历。")
        actions.append("把技能放进具体项目动作，例如接口测试、自动化脚本、缺陷定位、性能验证。")
        brutal_comments.append(
            "如果只写技能名，面试官很容易追问一句“你具体做了什么”，然后简历会失去说服力。"
        )
        evidence_gaps.append("缺项目证据：至少写清一个项目的目标、模块、职责、难点、结果。")
    if not has_metrics:
        risks.append("缺少量化结果，表达可信度和竞争力不足。")
        actions.append("给项目补充数量、覆盖范围、缺陷数、接口数、响应时间或效率提升等指标。")
        brutal_comments.append("没有数字的项目经历会显得很虚，像课程作业介绍，不像可投递作品。")
        evidence_gaps.append(
            "缺量化指标：用例数、接口数、缺陷数、响应时间、覆盖模块、优化前后对比。"
        )
    if not matched_tools:
        risks.append("工具链表达不足，无法证明你真的做过开发/测试/联调。")
        actions.append(
            "补充真实使用过的工具，例如 Flask、SQLite、Postman、JMeter、Pytest、Git 等。"
        )
        evidence_gaps.append("缺工具链证据：技术栈和工具要跟项目动作绑定，不要单独堆在技能栏。")
    else:
        strengths.append("工具链有可用基础：" + "、".join(matched_tools[:6]))
    if action_count < 2:
        risks.append("个人贡献不够清楚，容易被理解成只是参与或旁观。")
        actions.append("多使用“负责、设计、实现、验证、定位、推动修复、输出报告”等动作词。")
        evidence_gaps.append("缺个人动作：每条项目经历都要能看出你本人负责了哪一段。")
    if result_count < 1:
        actions.append("每段经历最后补一句结果：解决了什么问题、带来什么改进、沉淀了什么产物。")
        evidence_gaps.append("缺结果闭环：没有体现修复、提升、覆盖、稳定性或交付产物。")
    if missing:
        actions.append("把 JD 缺口关键词补进项目经历语境：" + "、".join(missing[:6]))
        brutal_comments.append("这份简历和目标 JD 还有明显错位，关键词不能硬塞，要落到项目动作里。")
        evidence_gaps.append("JD 缺口关键词：" + "、".join(missing[:8]))
    if matched:
        strengths.append("JD 已命中关键词：" + "、".join(matched[:8]))
    if not risks:
        risks.append("整体基础可用，下一步重点是让项目贡献更具体、更贴目标岗位。")
    if not brutal_comments:
        brutal_comments.append(
            "基础已经能看出方向，但还需要把“项目做了什么”升级成“你怎么判断、怎么实现、怎么验证”。"
        )
    if not strengths:
        strengths.append("已有内容可以作为初稿，但需要补充项目证据和岗位关键词后再投递。")
    return {
        "score": max(35, min(96, round(sum(section_scores.values()) / len(section_scores)))),
        "section_scores": section_scores,
        "positioning": (
            f"面向 {job_title or '目标岗位'} 的项目型候选人，"
            "核心卖点应落在真实项目、工具链、问题闭环和可验证结果。"
        ),
        "keywords": keywords,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "strengths": strengths,
        "brutal_comments": brutal_comments,
        "evidence_gaps": evidence_gaps,
        "risks": risks,
        "actions": actions,
        "project_suggestions": [
            "项目描述按“背景-目标-职责-动作-结果”组织，避免只写系统有什么功能。",
            "测试岗位要突出测试用例设计、接口验证、缺陷闭环、自动化/性能工具。",
            "AI 项目要说明模型网关、兜底策略、提示词设计、业务流程和异常处理。",
            (
                "把本系统写成可演示项目：多模型网关、简历/JD 分析、"
                "模拟面试状态流、语音表达评分、投递看板。"
            ),
            "每个亮点都配一条证据：接口、数据表、测试场景、异常处理或用户流程。",
        ],
    }


def tailor_resume_locally(
    resume_text: str,
    job_title: str,
    jd: str,
) -> dict[str, Any]:
    score, matched, missing = score_resume_against_jd(resume_text, jd)
    audit = build_resume_audit(resume_text, job_title, jd)
    rewritten = [
        f"求职意向：{job_title or '目标岗位'}",
        (
            "个人优势：具备 AI Web 系统项目实践，能围绕真实求职流程"
            "完成需求拆解、功能验证、接口验证和体验优化。"
        ),
        "",
        "项目经历改写示例：AI 智能体求职辅助 Web 系统",
        (
            "- 项目背景：面向应届生/转岗求职者，设计简历优化、JD 匹配、"
            "模拟面试、语音表达分析和投递追踪的一站式求职辅助系统。"
        ),
        (
            "- 个人职责：负责核心功能测试与体验优化，围绕简历上传解析、"
            "模型 API 兜底、JD 匹配分、面试状态流转设计测试场景。"
        ),
        (
            "- 技术与工具：Flask、SQLite、JavaScript、Selenium、Postman、"
            "JMeter、Pytest，覆盖功能测试、接口测试和基础性能验证。"
        ),
        (
            "- 结果产出：沉淀测试用例、缺陷记录、测试总结和可演示系统，"
            "将课程实训成果包装为可写入简历的完整项目经历。"
        ),
        "",
        "可量化表达模板：",
        (
            "- 将“参与测试”改为“设计 X 类核心用例，覆盖上传、匹配、"
            "面试、看板等主流程，发现并推动修复 X 个问题”。"
        ),
        "- 将“熟悉工具”改为“使用 JMeter 对关键接口进行并发压测，记录响应时间、错误率和瓶颈结论”。",
        "",
        "原始简历摘要：",
        resume_text[:900],
    ]
    return {
        "positioning": (
            f"面向 {job_title or '目标岗位'} 的候选人定位：具备项目实践、"
            "测试/开发工具链和 AI 应用理解，适合强调落地能力。"
        ),
        "match_score": score,
        "score_detail": audit["section_scores"],
        "brutal_comments": audit["brutal_comments"],
        "evidence_gaps": audit["evidence_gaps"],
        "jd_focus": extract_jd_focus(jd),
        "matched_keywords": matched,
        "keyword_gaps": missing,
        "keyword_strategy": matched + missing[:4],
        "tailored_resume": "\n".join(rewritten),
        "rewrite_tips": [
            "每段项目经历补充使用工具、负责动作、验证对象和结果。",
            "把“参与项目”改成“负责模块/设计用例/定位问题/输出报告”。",
            "关键词不要堆砌，放进真实项目语境里。",
        ],
        "interview_talking_points": [
            "为什么做这个系统：从真实求职痛点出发，解决简历、岗位、面试准备割裂的问题。",
            "技术亮点：多模型路由、本地兜底、面试状态机、语音表达指标分析。",
            "测试亮点：围绕主流程、异常输入、接口返回、模型不可用场景设计用例。",
        ],
    }

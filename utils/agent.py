"""
职途AI - ReAct Agent 执行器

核心设计：流程、工具、模型全部交给大模型自己决定。
- 工具集注册：把简历分析、JD匹配、面试题等能力封装成工具
- ReAct 循环：思考 → 行动 → 观察 → 再思考，直到 LLM 判断任务完成
- LLM 自主决策：调不调工具、调哪个、调几次、何时结束，全部由模型决定

增强项：
1. 多轮对话记忆：跨消息保持上下文，Agent 能引用之前说过的话
2. 工具错误恢复：工具执行失败时，把错误信息返回给 LLM，让它自己决定怎么办
3. 追问能力：信息不足时 Agent 会主动向用户追问，而不是瞎猜
4. 观察结果截断：防止长文本撑爆上下文窗口
5. 最多 5 轮循环限制：防止 Agent 陷入死循环
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from utils.ai_client import get_ai_client


# ==================== 多轮对话记忆 ====================
# 保存最近几轮的对话历史，让 Agent 能引用之前的上下文
# 最多保留 20 条消息（约 10 轮对话），超出自动丢弃最早的

MAX_MEMORY_MESSAGES = 20
_conversation_history: List[dict] = []


def _add_to_memory(role: str, content: str) -> None:
    """把一条消息加入对话记忆"""
    _conversation_history.append({"role": role, "content": content})
    # 超出上限时丢弃最早的消息
    if len(_conversation_history) > MAX_MEMORY_MESSAGES:
        _conversation_history.pop(0)


def _get_memory_messages() -> List[dict]:
    """获取对话记忆（不包含 system prompt，system 单独传）"""
    return list(_conversation_history)


def clear_memory() -> None:
    """清空对话记忆"""
    _conversation_history.clear()


# ==================== 工具定义 ====================

TOOL_DEFINITIONS = [
    {
        "name": "analyze_resume",
        "description": "分析简历内容，从岗位匹配、项目含金量、表达质量、量化结果、风险点五个维度给出诊断。当用户想了解简历质量、找简历问题时使用。",
        "parameters": "resume_text (必填, 简历文本内容)",
    },
    {
        "name": "match_job",
        "description": "将简历与目标岗位JD进行匹配，给出0-100匹配分、已命中能力、技能缺口和投递建议。当用户想看自己和某个岗位的匹配度时使用。",
        "parameters": "resume_text (必填), job_title (必填, 岗位名称), jd (选填, 岗位描述)",
    },
    {
        "name": "get_interview_question",
        "description": "从面试题库中获取指定方向的面试题。当用户想练习面试、获取面试题时使用。",
        "parameters": "category (选填, 如 python/java/frontend/test/general, 默认general)",
    },
    {
        "name": "evaluate_answer",
        "description": "评估用户对面试题的回答，从完整性、逻辑性、技术深度、表达能力打分。当用户回答了面试题想要反馈时使用。",
        "parameters": "question (必填, 面试题), answer (必填, 用户的回答)",
    },
    {
        "name": "analyze_jd",
        "description": "智能解析岗位JD，提取核心要求、技能关键词、能力维度。当用户粘贴了一段JD想了解岗位需求时使用。",
        "parameters": "jd_text (必填, JD原文)",
    },
    {
        "name": "evaluate_salary",
        "description": "根据城市、经验、技能数量评估合理薪资范围。当用户想了解某岗位薪资水平时使用。",
        "parameters": "city (选填, 如 北京/上海), experience (选填, 如 应届生/1-3年), skills_count (选填, 技能数量)",
    },
    {
        "name": "get_user_resumes",
        "description": "获取用户已保存的简历列表。当需要查看用户有哪些简历、获取简历内容时使用。",
        "parameters": "user_id (选填, 默认1)",
    },
    {
        "name": "get_user_applications",
        "description": "获取用户投递记录，包括公司、岗位、状态。当用户想了解投递情况、跟进进度时使用。",
        "parameters": "user_id (选填, 默认1)",
    },
    {
        "name": "ask_user",
        "description": "当信息不足、需要用户补充更多细节时使用。比如用户说'帮我分析简历'但没提供简历内容。",
        "parameters": "question (必填, 想问用户的问题)",
    },
    {
        "name": "web_search",
        "description": "联网搜索互联网信息，获取实时新闻、技术文档、公司信息、面试经验等外部内容。当用户问的问题需要最新信息或你自身知识不足时使用。",
        "parameters": "query (必填, 搜索关键词)",
    },
    {
        "name": "get_weather",
        "description": "查询指定城市的实时天气信息，包括温度、天气状况、风力、湿度。当用户问天气相关问题时使用。",
        "parameters": "city (必填, 城市名如 北京/上海/深圳)",
    },
    {
        "name": "fetch_webpage",
        "description": "抓取指定网页的文本内容，用于深入了解某个链接的详细信息。当搜索结果中某个网页需要进一步阅读时使用。",
        "parameters": "url (必填, 网页地址)",
    },
]


def _build_tool_schema_text() -> str:
    """生成工具清单文本，告诉 LLM 有哪些工具可用"""
    lines = []
    for t in TOOL_DEFINITIONS:
        lines.append(f"- 工具名：{t['name']}\n  功能：{t['description']}\n  参数：{t['parameters']}")
    return "\n".join(lines)


# ==================== 工具执行函数 ====================

def _exec_analyze_resume(params: dict, db_path: str) -> str:
    client = get_ai_client()
    resume_text = params.get("resume_text", "")
    if not resume_text or len(resume_text) < 10:
        return "[工具错误] 缺少 resume_text 参数或内容太短，请先用 ask_user 工具向用户索要简历内容"
    result = client.analyze_resume(resume_text)
    return result.get("content", "分析失败")


def _exec_match_job(params: dict, db_path: str) -> str:
    client = get_ai_client()
    resume_text = params.get("resume_text", "")
    if not resume_text:
        return "[工具错误] 缺少 resume_text 参数，请先用 ask_user 工具向用户索要简历内容"
    result = client.match_job(
        resume_text,
        params.get("job_title", "目标岗位"),
        params.get("jd", ""),
    )
    return result.get("content", "匹配失败")


def _exec_get_interview_question(params: dict, db_path: str) -> str:
    try:
        from config import INTERVIEW_QUESTIONS
        category = params.get("category", "general")
        questions = INTERVIEW_QUESTIONS.get(category, INTERVIEW_QUESTIONS.get("general", []))
        if not questions:
            return f"暂无 {category} 方向的面试题"
        import random
        q = random.choice(questions)
        if isinstance(q, dict):
            return f"面试题：{q.get('question', '')}\n\n参考答案：{q.get('answer', '暂无答案')}"
        return f"面试题：{q}"
    except Exception as e:
        return f"[工具错误] 获取面试题失败：{e}"


def _exec_evaluate_answer(params: dict, db_path: str) -> str:
    question = params.get("question", "")
    answer = params.get("answer", "")
    if not answer:
        return "[工具错误] 缺少 answer 参数，请先用 ask_user 工具让用户回答问题"
    from utils.interview_engine import InterviewEngine
    engine = InterviewEngine()
    engine.candidate_answers = [answer]
    result = engine.evaluate()
    return f"评分：{result['score']}分\n反馈：{result['feedback']}\nAI评价：{result['ai_comment']}"


def _exec_analyze_jd(params: dict, db_path: str) -> str:
    client = get_ai_client()
    jd_text = params.get("jd_text", "")
    if not jd_text or len(jd_text) < 10:
        return "[工具错误] 缺少 jd_text 参数，请先用 ask_user 工具向用户索要 JD 原文"
    result = client.chat([
        {"role": "system", "content": "你是岗位分析专家。请解析JD，提取：1 核心要求 2 必备技能 3 加分技能 4 能力维度 5 面试可能考察点。用中文回答。"},
        {"role": "user", "content": jd_text[:3000]},
    ])
    return result.get("content", "解析失败")


def _exec_evaluate_salary(params: dict, db_path: str) -> str:
    city = params.get("city", "")
    experience = params.get("experience", "应届生")
    skills_count = int(params.get("skills_count", 0) or 0)
    city_factor = {"北京": 1.25, "上海": 1.25, "深圳": 1.2, "广州": 1.05, "杭州": 1.15, "成都": 0.9}.get(city, 1)
    base = {"应届生": 9000, "1-3年": 15000, "3-5年": 24000, "5年以上": 36000}.get(experience, 12000)
    skills_bonus = min(5000, skills_count * 500)
    avg = int((base + skills_bonus) * city_factor)
    return f"薪资评估结果：\n城市：{city or '未指定'}\n经验：{experience}\n建议薪资范围：{int(avg*0.75)}-{int(avg*1.35)}元/月\n平均值：{avg}元/月"


def _exec_get_user_resumes(params: dict, db_path: str) -> str:
    user_id = int(params.get("user_id", 1))
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, title, substr(content,1,200) as preview FROM resumes WHERE user_id=? ORDER BY updated_at DESC LIMIT 5",
            (user_id,)
        ).fetchall()
        conn.close()
        if not rows:
            return "用户暂无保存的简历"
        lines = [f"简历ID:{r['id']} | 标题:{r['title']} | 预览:{r['preview']}..." for r in rows]
        return "\n".join(lines)
    except Exception as e:
        return f"[工具错误] 查询简历失败：{e}"


def _exec_get_user_applications(params: dict, db_path: str) -> str:
    user_id = int(params.get("user_id", 1))
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT company, job_title, status, city FROM job_applications WHERE user_id=? ORDER BY updated_at DESC LIMIT 8",
            (user_id,)
        ).fetchall()
        conn.close()
        if not rows:
            return "用户暂无投递记录"
        lines = [f"公司:{r['company']} | 岗位:{r['job_title']} | 状态:{r['status']} | 城市:{r['city'] or '未填'}" for r in rows]
        return "\n".join(lines)
    except Exception as e:
        return f"[工具错误] 查询投递记录失败：{e}"


def _exec_ask_user(params: dict, db_path: str) -> str:
    """追问工具：信息不足时让 Agent 主动向用户提问"""
    question = params.get("question", "请提供更多信息")
    return f"[需要用户补充信息] {question}"


def _exec_web_search(params: dict, db_path: str) -> str:
    """联网搜索：多源搜索，DuckDuckGo + Wikipedia + 百度百科"""
    import requests as req

    query = params.get("query", "").strip()
    if not query:
        return "[工具错误] 缺少 query 参数"

    results = []

    # 方式1：DuckDuckGo Instant Answer API（免费、无需 Key，超时3秒）
    try:
        resp = req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=3,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("Abstract", "")
            if abstract:
                results.append(f"[摘要] {abstract}")
            for topic in (data.get("RelatedTopics") or [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"[相关] {topic['Text'][:200]}")
            definition = data.get("Definition", "")
            if definition:
                results.append(f"[定义] {definition}")
    except Exception:
        pass

    # 方式2：Wikipedia 中文百科（超时3秒）
    if not results:
        try:
            resp2 = req.get(
                "https://zh.wikipedia.org/api/rest_v1/page/summary/" + req.utils.quote(query),
                timeout=3,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp2.status_code == 200:
                wiki = resp2.json()
                extract = wiki.get("extract", "")
                if extract:
                    results.append(f"[百科] {extract[:500]}")
        except Exception:
            pass

    # 方式3：Wikipedia 英文（超时3秒）
    if not results:
        try:
            resp3 = req.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" + req.utils.quote(query),
                timeout=3,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp3.status_code == 200:
                wiki = resp3.json()
                extract = wiki.get("extract", "")
                if extract:
                    results.append(f"[Encyclopedia] {extract[:500]}")
        except Exception:
            pass

    if not results:
        return f"搜索未找到关于「{query}」的相关信息。可能是网络受限，建议换个关键词或稍后再试。"

    return f"搜索「{query}」的结果：\n\n" + "\n\n".join(results)


def _exec_get_weather(params: dict, db_path: str) -> str:
    """天气查询：使用 Open-Meteo 免费 API（无需 Key）"""
    import requests as req

    city = params.get("city", "").strip()
    if not city:
        return "[工具错误] 缺少 city 参数"

    # 第1步：城市名 → 经纬度（用 Open-Meteo Geocoding API）
    try:
        geo_resp = req.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "zh", "format": "json"},
            timeout=8,
        )
        if geo_resp.status_code != 200:
            return f"查询「{city}」天气失败：地理编码服务无响应"

        geo = geo_resp.json()
        locations = geo.get("results", [])
        if not locations:
            return f"未找到城市「{city}」，请确认城市名"

        loc = locations[0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        full_name = loc.get("name", city)
        if loc.get("admin1"):
            full_name += f"（{loc['admin1']}）"
    except Exception as e:
        return f"地理编码失败：{e}"

    # 第2步：经纬度 → 天气（用 Open-Meteo Forecast API）
    try:
        weather_resp = req.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Shanghai",
            },
            timeout=8,
        )
        if weather_resp.status_code != 200:
            return f"查询「{city}」天气失败：天气服务无响应"

        w = weather_resp.json().get("current", {})
        temp = w.get("temperature_2m", "?")
        humidity = w.get("relative_humidity_2m", "?")
        wind = w.get("wind_speed_10m", "?")
        code = w.get("weather_code", 0)

        # WMO 天气码 → 中文描述
        weather_map = {
            0: "晴", 1: "大致晴朗", 2: "局部多云", 3: "阴",
            45: "雾", 48: "雾凇", 51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
            61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪",
            80: "阵雨", 81: "中阵雨", 82: "大阵雨", 95: "雷暴", 96: "雷暴夹冰雹", 99: "雷暴夹冰雹",
        }
        weather_text = weather_map.get(code, f"天气码{code}")

        return (
            f"📍 {full_name} 实时天气\n"
            f"🌡 温度：{temp}°C\n"
            f"🌤 天气：{weather_text}\n"
            f"💧 湿度：{humidity}%\n"
            f"💨 风速：{wind} km/h"
        )
    except Exception as e:
        return f"天气查询失败：{e}"


def _exec_fetch_webpage(params: dict, db_path: str) -> str:
    """网页抓取：获取指定 URL 的文本内容"""
    import requests as req
    import re as _re

    url = params.get("url", "").strip()
    if not url:
        return "[工具错误] 缺少 url 参数"

    if not url.startswith("http"):
        url = "https://" + url

    try:
        resp = req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return f"抓取失败：HTTP {resp.status_code}"

        html = resp.text
        # 简易 HTML → 纯文本
        # 去掉 script 和 style
        html = _re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=_re.DOTALL | _re.IGNORECASE)
        # 去掉所有标签
        text = _re.sub(r"<[^>]+>", " ", html)
        # 去掉多余空白
        text = _re.sub(r"\s+", " ", text).strip()

        if not text:
            return f"抓取到了网页但未提取到文本内容"

        # 截断到 1500 字
        if len(text) > 1500:
            text = text[:1500] + "...[内容已截断]"

        return f"网页内容（{url}）：\n\n{text}"
    except Exception as e:
        return f"网页抓取失败：{e}"


TOOL_EXECUTORS: Dict[str, Callable] = {
    "analyze_resume": _exec_analyze_resume,
    "match_job": _exec_match_job,
    "get_interview_question": _exec_get_interview_question,
    "evaluate_answer": _exec_evaluate_answer,
    "analyze_jd": _exec_analyze_jd,
    "evaluate_salary": _exec_evaluate_salary,
    "get_user_resumes": _exec_get_user_resumes,
    "get_user_applications": _exec_get_user_applications,
    "ask_user": _exec_ask_user,
    "web_search": _exec_web_search,
    "get_weather": _exec_get_weather,
    "fetch_webpage": _exec_fetch_webpage,
}


# ==================== ReAct Agent 执行器 ====================

SYSTEM_PROMPT = """你是职途AI求职Agent，一个能够自主思考和调用工具的智能体。

你有以下工具可以使用：

{tools}

## 你的工作方式（ReAct 框架）

每次收到用户消息，你必须按以下格式思考和行动：

思考：分析用户的需求，判断需要什么信息、是否需要调用工具。
行动：工具名称（或"直接回答"）
参数：JSON格式的参数，如 {{"resume_text": "...", "job_title": "..."}}
（如果行动是"直接回答"，则不需要参数，直接在下一行写回答内容）

## 关键规则

1. 简单问题（打招呼、闲聊、通用建议）→ 不需要工具，直接回答
2. 需要分析的问题 → 先思考需要什么信息，调用对应工具
3. 一次工具调用不够 → 可以继续思考、继续调用其他工具
4. 拿到足够信息后 → 行动写"任务完成"，然后整理最终回答
5. 你可以连续调用多个工具，直到你认为信息足够为止
6. 每次只能调用一个工具
7. 如果工具返回 [工具错误] 或 [需要用户补充信息] → 立即输出"行动：任务完成"，把问题转达给用户
8. 如果用户问题不完整（比如"帮我分析简历"但没给简历内容）→ 使用 ask_user 工具向用户提问
9. 需要最新信息、外部知识、新闻资讯 → 使用 web_search 联网搜索
10. 需要天气信息 → 使用 get_weather 查询实时天气
11. 需要深入阅读某个网页 → 先 web_search 搜索，再用 fetch_webpage 抓取具体网页

## 示例

用户：帮我看看我的简历有什么问题
思考：用户想分析简历，但我需要先获取用户的简历内容。先调用get_user_resumes获取简历列表。
行动：get_user_resumes
参数：{{"user_id": 1}}

（系统返回简历列表后）

思考：用户有一份简历，ID为1。现在调用analyze_resume分析这份简历的内容。
行动：analyze_resume
参数：{{"resume_text": "..."}}

（系统返回分析结果后）

思考：已经获取到简历分析结果，信息充足，可以整理最终回答了。
行动：任务完成
（然后整理最终回答给用户）

用户：帮我分析简历
思考：用户想分析简历，但没有提供简历内容，也没有保存的简历。我需要先问用户要简历内容。
行动：ask_user
参数：{{"question": "请把你的简历内容发给我，我来帮你分析。你也可以在简历实验室页面保存简历后再来。"}}

（系统返回 [需要用户补充信息] 后）

思考：需要用户补充信息，我应该把这个问题转达给用户。
行动：任务完成
请把你的简历内容发给我，我来帮你分析。你也可以在简历实验室页面保存简历后再来。
"""


def _parse_react_response(text: str) -> dict:
    """解析 LLM 的 ReAct 格式输出"""
    result = {"thought": "", "action": "", "params": "", "finished": False, "final_answer": ""}

    # 提取思考
    thought_match = re.search(r"思考[：:]\s*(.+?)(?=行动[：:]|$)", text, re.DOTALL)
    if thought_match:
        result["thought"] = thought_match.group(1).strip()

    # 提取行动
    action_match = re.search(r"行动[：:]\s*(.+?)(?=参数[：:]|思考[：:]|$)", text, re.DOTALL)
    if action_match:
        action = action_match.group(1).strip()
        result["action"] = action
        if action in ("直接回答", "任务完成", "完成"):
            result["finished"] = True
            # 提取最终回答（行动之后的所有内容）
            final_match = re.search(r"行动[：:]\s*(?:直接回答|任务完成|完成)\s*\n?(.*)", text, re.DOTALL)
            if final_match:
                result["final_answer"] = final_match.group(1).strip()

    # 提取参数
    params_match = re.search(r"参数[：:]\s*(.+?)(?=思考[：:]|行动[：:]|$)", text, re.DOTALL)
    if params_match:
        result["params"] = params_match.group(1).strip()

    return result


def _truncate(text: str, max_len: int = 1500) -> str:
    """截断长文本，防止撑爆上下文窗口"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[内容已截断，仅显示前1500字]"


def run_agent(
    user_message: str,
    context: str = "",
    db_path: str = "",
    max_iterations: int = 5,
) -> dict:
    """
    执行 ReAct Agent 循环。

    返回:
        {
            "reply": 最终回答,
            "iterations": 执行了几轮,
            "trace": 每轮的思考-行动-观察记录,
            "tools_used": 使用了哪些工具,
            "ai_used": 是否用了大模型,
        }
    """
    client = get_ai_client()
    tools_text = _build_tool_schema_text()
    system = SYSTEM_PROMPT.replace("{tools}", tools_text)

    # 把用户消息存入对话记忆
    _add_to_memory("user", user_message)

    # 构建完整消息：system prompt + 对话记忆 + 当前问题
    messages = [{"role": "system", "content": system}]
    # 加入历史对话记忆（最近几轮）
    memory = _get_memory_messages()
    # 排除最后一条（刚加入的当前问题），因为下面会单独加
    if len(memory) > 1:
        for msg in memory[:-1]:
            messages.append(msg)
    # 当前用户问题 + 上下文
    messages.append({
        "role": "user",
        "content": f"上下文：{context[:800]}\n\n用户问题：{user_message}",
    })

    trace = []
    tools_used = []

    # ===== 降级模式：无 API Key 时，用意图识别模拟 Agent 工具选择 =====
    if not client.api_key:
        result = _run_local_agent(user_message, context, db_path, trace, tools_used)
        _add_to_memory("assistant", result["reply"])
        return result

    for i in range(max_iterations):
        # 1. LLM 思考并决定下一步行动
        result = client.chat(messages, temperature=0.4, max_tokens=800)
        llm_output = result.get("content", "")

        trace.append({
            "iteration": i + 1,
            "type": "thought",
            "content": llm_output[:500],
        })

        # 2. 解析 LLM 输出
        parsed = _parse_react_response(llm_output)

        # 3. 判断是否完成
        if parsed["finished"]:
            final = parsed["final_answer"] or llm_output
            if not final and parsed["action"] == "直接回答":
                final = llm_output.split("行动：直接回答")[-1].strip() if "直接回答" in llm_output else llm_output
            if not final:
                final = llm_output
            # 存入对话记忆
            _add_to_memory("assistant", final)
            return {
                "reply": final,
                "iterations": i + 1,
                "trace": trace,
                "tools_used": tools_used,
                "ai_used": result.get("success", False),
            }

        # 4. 执行工具
        action = parsed["action"]
        if action not in TOOL_EXECUTORS:
            _add_to_memory("assistant", llm_output)
            return {
                "reply": llm_output,
                "iterations": i + 1,
                "trace": trace,
                "tools_used": tools_used,
                "ai_used": result.get("success", False),
            }

        # 解析参数
        params = {}
        if parsed["params"]:
            try:
                params = json.loads(parsed["params"])
            except json.JSONDecodeError:
                params = {"raw": parsed["params"]}

        # 执行工具（带错误恢复）
        try:
            observation = TOOL_EXECUTORS[action](params, db_path)
        except Exception as e:
            observation = f"[工具执行异常] {action} 调用失败：{e}"

        # 截断观察结果，防止上下文过长
        observation = _truncate(observation)
        tools_used.append(action)

        trace.append({
            "iteration": i + 1,
            "type": "action",
            "action": action,
            "params": params,
            "observation": observation[:500],
        })

        # 5. 检查是否需要向用户追问
        if action == "ask_user" or "[需要用户补充信息]" in observation:
            # Agent 判断信息不足，需要追问用户
            _add_to_memory("assistant", observation)
            return {
                "reply": observation.replace("[需要用户补充信息] ", ""),
                "iterations": i + 1,
                "trace": trace,
                "tools_used": tools_used,
                "ai_used": result.get("success", False),
            }

        # 6. 把工具返回结果塞回上下文，让 LLM 再次思考
        messages.append({"role": "assistant", "content": llm_output})
        messages.append({
            "role": "user",
            "content": f"工具【{action}】返回结果：\n{observation}\n\n请根据以上结果继续思考，决定下一步行动。如果信息足够，请输出[行动：任务完成]并给出最终回答。如果工具返回了错误，请告知用户并提供替代方案。",
        })

    # 超过最大轮次，让 LLM 做最终总结
    messages.append({
        "role": "user",
        "content": "已达到最大工具调用次数。请根据已有信息，直接给出最终回答。",
    })
    final_result = client.chat(messages, temperature=0.5, max_tokens=800)
    final_reply = final_result.get("content", "抱歉，处理超时，请重试。")
    _add_to_memory("assistant", final_reply)
    return {
        "reply": final_reply,
        "iterations": max_iterations,
        "trace": trace,
        "tools_used": tools_used,
        "ai_used": final_result.get("success", False),
    }


# ==================== 降级模式：无 API Key 时的本地 Agent ====================

def _run_local_agent(user_message: str, context: str, db_path: str, trace: list, tools_used: list) -> dict:
    """
    无 API Key 时的降级 Agent。
    用关键词意图识别来决定调用哪些工具，模拟 Agent 的工具选择行为。

    注意：这是降级模式，不是真正的 Agent。
    真正的 Agent 行为在配置 API Key 后由 LLM 自主决策。
    """
    msg = user_message.lower()
    observations = []

    intent_rules = [
        (["分析简历", "简历问题", "简历诊断", "简历分析", "看看简历"], "analyze_resume", {"resume_text": context[:2000] if context else ""}),
        (["匹配岗位", "岗位匹配", "jd匹配", "适合吗", "匹配度"], "match_job", {"resume_text": context[:2000] if context else "", "job_title": "目标岗位", "jd": ""}),
        (["面试题", "练习面试", "考题", "来一道题", "出一道题"], "get_interview_question", {"category": "general"}),
        (["解析jd", "岗位描述", "分析jd", "jd分析"], "analyze_jd", {"jd_text": user_message[:2000]}),
        (["薪资多少", "工资多少", "待遇多少", "评估薪资", "薪资水平"], "evaluate_salary", {"city": "", "experience": "应届生"}),
        (["投递记录", "投递进度", "申请记录", "投递情况"], "get_user_applications", {"user_id": 1}),
        (["简历列表", "我的简历", "有哪些简历", "查看简历"], "get_user_resumes", {"user_id": 1}),
        # 外部工具：联网搜索
        (["搜索", "查一下", "查查", "百度", "谷歌", "最新", "新闻", "是什么", "是什么意思", "什么是", "介绍", "解释一下", "告诉我"], "web_search", {"query": user_message[:100]}),
        # 外部工具：天气查询
        (["天气", "气温", "下雨吗", "冷吗", "热吗", "穿什么"], "get_weather", {"city": _extract_city(msg)}),
    ]

    selected_tools = []
    for keywords, tool_name, params in intent_rules:
        if any(kw in msg for kw in keywords):
            selected_tools.append((tool_name, params))

    if not selected_tools:
        trace.append({
            "iteration": 1,
            "type": "thought",
            "content": "本地降级模式：用户问题不匹配任何工具意图，直接回答。",
        })
        return {
            "reply": _local_chat_response(user_message, context),
            "iterations": 1,
            "trace": trace,
            "tools_used": [],
            "ai_used": False,
        }

    for tool_name, params in selected_tools[:3]:
        trace.append({
            "iteration": len(tools_used) + 1,
            "type": "thought",
            "content": f"本地降级模式：检测到用户意图匹配 [{tool_name}]，调用该工具。",
        })
        trace.append({
            "iteration": len(tools_used) + 1,
            "type": "action",
            "action": tool_name,
            "params": params,
        })

        executor = TOOL_EXECUTORS.get(tool_name)
        if executor:
            try:
                observation = executor(params, db_path)
            except Exception as e:
                observation = f"[工具执行异常] {tool_name} 失败：{e}"
            observations.append(f"[{tool_name}] 结果：\n{observation}")
            tools_used.append(tool_name)

            trace.append({
                "iteration": len(tools_used),
                "type": "observation",
                "observation": observation[:500],
            })

    if observations:
        reply = "## Agent 分析结果（本地降级模式）\n\n"
        reply += "我自主选择了以下工具来处理你的问题：\n"
        reply += " -> ".join(tools_used) + "\n\n"
        reply += "---\n\n"
        reply += "\n\n".join(observations)
        reply += "\n\n---\n"
        reply += "\n💡 配置 API Key 后，Agent 将由大模型自主思考决策，支持更灵活的工具组合和推理。"
    else:
        reply = _local_chat_response(user_message, context)

    return {
        "reply": reply,
        "iterations": len(tools_used),
        "trace": trace,
        "tools_used": tools_used,
        "ai_used": False,
    }


def _extract_city(msg: str) -> str:
    """从用户消息中提取城市名"""
    cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "西安", "重庆",
              "苏州", "天津", "长沙", "青岛", "大连", "厦门", "无锡", "合肥", "郑州", "济南",
              "沈阳", "哈尔滨", "长春", "昆明", "贵阳", "南宁", "兰州", "太原", "石家庄", "福州",
              "南昌", "珠海", "东莞", "佛山", "宁波", "温州"]
    for c in cities:
        if c in msg:
            return c
    return "北京"  # 默认


def _local_chat_response(user_message: str, context: str) -> str:
    """无工具调用时的本地回答 — 支持日期、时间、简单问答等通用能力"""
    from datetime import datetime
    import calendar

    msg = user_message.lower().strip()

    # --- 日期/时间类问题 ---
    weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()

    if any(w in msg for w in ["周几", "星期几", "今天周", "今天星期", "今天几号", "今天多少号", "今天日期", "今天几号"]):
        if "几号" in msg or "多少号" in msg or "日期" in msg:
            return f"今天是 {now.year}年{now.month}月{now.day}日，{weekdays_cn[now.weekday()]}。"
        return f"今天是{weekdays_cn[now.weekday()]}，{now.year}年{now.month}月{now.day}日。"

    if any(w in msg for w in ["几点", "现在时间", "什么时间", "现在几点"]):
        return f"现在是 {now.strftime('%H:%M')}，{weekdays_cn[now.weekday()]}。"

    if "今天" in msg and ("月" in msg or "日" in msg):
        return f"今天是 {now.year}年{now.month}月{now.day}日。"

    if "这个月" in msg and ("几" in msg or "什么" in msg):
        return f"这个月是 {now.month} 月。"

    if "今年" in msg and ("几" in msg or "什么" in msg):
        return f"今年是 {now.year} 年。"

    # --- 简单问答 ---
    if any(w in msg for w in ["你好", "hi", "hello", "在吗", "嗨"]):
        return "你好！我是职途AI求职Agent。我可以帮你：\n1. 分析简历问题\n2. 匹配岗位JD\n3. 获取面试题\n4. 评估面试回答\n5. 解析岗位JD\n6. 评估薪资\n7. 查看投递记录\n\n告诉我你需要什么帮助？"

    if any(w in msg for w in ["你是谁", "你能做什么", "功能", "agent", "智能体", "你是agent吗"]):
        return "我是职途AI求职Agent，一个基于 ReAct 框架的智能体。我有 9 个工具可用，会根据你的问题自主选择合适的工具来处理。\n\n与普通聊天机器人不同，我会先思考需要什么信息，然后选择工具执行，拿到结果后继续思考，直到信息足够才给你最终回答。\n\n试试问我：[帮我分析简历] [给我一道面试题] [这个岗位适合我吗]"

    if any(w in msg for w in ["谢谢", "感谢", "thx", "thanks"]):
        return "不客气！有其他问题随时问我。"

    if any(w in msg for w in ["再见", "拜拜", "bye", "88"]):
        return "再见！祝你求职顺利，Offer 拿到手软！"

    if any(w in msg for w in ["吃饭", "吃什么", "午餐", "晚饭", "早餐"]):
        return "这个问题超出了我的求职专长范围 😄 不过说到吃饭，吃饱了才有力气面试！建议先填饱肚子，然后回来练习面试题。"

    if any(w in msg for w in ["天气", "下雨", "出太阳"]):
        return "我可以帮你查实时天气！请告诉我你想查哪个城市的天气，比如'北京天气怎么样'。"

    if any(w in msg for w in ["笑话", "讲个", "无聊", "郁闷", "焦虑", "紧张"]):
        return "面试紧张很正常！给你讲个程序员的笑话：\n\n面试官：你最大的缺点是什么？\n程序员：我太诚实。\n面试官：我不觉得诚实是缺点。\n程序员：我不在乎你怎么想。\n\n好了，笑完回来练习面试吧！"

    # --- 常识类简单问题 ---
    if "1+1" in msg or "1 + 1" in msg:
        return "1+1=2。这种问题可以直接问我，不需要调用任何工具。"

    if any(w in msg for w in ["你是ai吗", "你是机器人吗", "你是真人吗", "你是人工智能吗"]):
        return "我是 AI Agent，不是真人。我基于 ReAct 框架运行，能自主思考、调用 12 个工具（包括联网搜索和天气查询）来帮你解决求职问题。"

    # --- 默认回答 ---
    # 尝试识别更多简单问题，避免无脑返回模板
    if len(msg) < 15 and msg.endswith("吗"):
        # 简单的是非问题
        return f"这个问题取决于具体情况。作为求职Agent，我更擅长帮你解决简历、面试、岗位匹配等问题。你要不要试试问我这些方面的内容？"

    return f"我理解你的问题：{user_message}\n\n这个问题超出了我的求职工具范围，但我可以帮你做这些：\n1. 分析简历问题\n2. 匹配岗位JD\n3. 获取面试题\n4. 评估面试回答\n5. 解析岗位JD\n6. 评估薪资\n7. 联网搜索信息\n8. 查询实时天气\n\n要不要试试？"

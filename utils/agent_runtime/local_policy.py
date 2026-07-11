from __future__ import annotations

from utils.agent_runtime.models import AgentDecision


class LocalPolicy:
    """Deterministic no-key policy. It never claims to be model reasoning."""

    ai_used = False
    provider = "local"
    model = "local-policy"

    def decide(self, state, tool_schemas) -> AgentDecision:
        if state.observations:
            latest = state.observations[-1]
            return AgentDecision("final", message=latest["display_text"])

        if state.active_task:
            task_type = state.active_task["task_type"]
            if task_type == "match_job":
                job_title = state.user_message.strip()
                if len(job_title) < 2:
                    return AgentDecision(
                        "needs_input",
                        arguments={"task_type": "match_job", "slots": state.active_task["slots"]},
                        message="请告诉我目标岗位名称，例如 Python 测试工程师。",
                    )
                slots = {**state.active_task["slots"], "job_title": job_title}
                return AgentDecision("tool_call", "match_job", slots)

        message = state.user_message.lower().strip()
        if any(word in message for word in ("匹配岗位", "岗位匹配", "匹配度", "适合这个岗位")):
            return AgentDecision(
                "needs_input",
                arguments={"task_type": "match_job", "slots": {}},
                message="请告诉我目标岗位名称；有 JD 的话也可以一起发来。",
            )
        if any(word in message for word in ("看板", "整体进度", "整体情况", "求职进度")):
            return AgentDecision("tool_call", "get_dashboard", {})
        if any(word in message for word in ("简历列表", "有哪些简历", "我的简历")):
            return AgentDecision("tool_call", "list_resumes", {})
        if any(word in message for word in ("分析简历", "简历问题", "简历诊断")):
            return AgentDecision("tool_call", "analyze_resume", {})
        if any(word in message for word in ("投递", "申请记录")):
            return AgentDecision("tool_call", "list_applications", {})
        if any(word in message for word in ("求职报告", "作战报告", "阶段总结")):
            return AgentDecision("tool_call", "generate_career_report", {})
        if any(word in message for word in ("面试题", "来一道题", "练习面试")):
            return AgentDecision("tool_call", "get_interview_question", {})
        if any(word in message for word in ("薪资", "工资", "待遇")):
            return AgentDecision("tool_call", "evaluate_salary", {})
        if any(word in message for word in ("你好", "您好", "嗨", "hello")):
            return AgentDecision(
                "final",
                message="你好，我可以结合你保存的简历、面试和投递数据，帮你推进下一步求职行动。",
            )
        return AgentDecision(
            "final",
            message=(
                "当前未配置大模型 API，我可以继续执行简历查询、岗位匹配、面试题、"
                "投递看板和求职报告等本地任务。请告诉我你现在最想推进哪一步。"
            ),
        )

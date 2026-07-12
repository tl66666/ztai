from __future__ import annotations

import re

from utils.agent_runtime.models import AgentDecision


_APPLICATION_STATUSES = (
    "意向", "准备中", "已投递", "简历筛选", "笔试", "一面", "二面",
    "HR 面", "Offer", "已拒绝", "已结束",
)
_NON_WRITE_REQUEST = re.compile(
    r"查看|查询|哪些|有没有|保存过|创建过|新增的|怎么|如何|能否介绍|能不能介绍|请介绍"
)
_POLITE_PREFIX = r"^(?:请|麻烦)?(?:帮我)?"


class LocalPolicy:
    """Deterministic no-key policy. It never claims to be model reasoning."""

    ai_used = False
    provider = "local"
    model = "local-policy"

    def decide(self, state, tool_schemas) -> AgentDecision:
        if state.observations:
            latest = state.observations[-1]
            return AgentDecision(
                "final", message=f"本地规则模式：{latest['display_text']}"
            )

        if state.active_task:
            task_type = state.active_task["task_type"]
            if task_type == "career_action":
                return self._continue_career_action(
                    state.active_task.get("slots") or {}, state.user_message
                )
            if task_type == "match_job":
                job_title = state.user_message.strip()
                if len(job_title) < 2:
                    return AgentDecision(
                        "needs_input",
                        arguments={"task_type": "match_job", "slots": state.active_task["slots"]},
                        message="本地规则模式：请告诉我目标岗位名称，例如 Python 测试工程师。",
                    )
                slots = {**state.active_task["slots"], "job_title": job_title}
                return AgentDecision("tool_call", "match_job", slots)

        message = state.user_message.strip()
        lowered = message.lower()
        action_type = self._explicit_action_type(message)
        if action_type:
            return self._start_career_action(action_type, message)

        if "简历" in message and any(
            word in message for word in ("刚才", "这个岗位", "目标岗位", "岗位看看")
        ):
            remembered_role = re.search(r"target_role：([^\n]+)", state.context_prompt)
            if remembered_role:
                return AgentDecision(
                    "tool_call",
                    "match_job",
                    {"job_title": remembered_role.group(1).strip()},
                )
        if any(word in message for word in ("匹配岗位", "岗位匹配", "匹配度", "适合这个岗位")):
            return AgentDecision(
                "needs_input",
                arguments={"task_type": "match_job", "slots": {}},
                message="本地规则模式：请告诉我目标岗位名称；有 JD 的话也可以一起发来。",
            )
        if any(word in message for word in ("看板", "整体进度", "整体情况", "求职进度")):
            return AgentDecision("tool_call", "get_dashboard", {})
        if any(word in message for word in ("简历列表", "有哪些简历", "我的简历")):
            return AgentDecision("tool_call", "list_resumes", {})
        if any(word in message for word in ("分析简历", "简历问题", "简历诊断")):
            return AgentDecision("tool_call", "analyze_resume", {})
        # “投递” alone is always a read. A write requires an explicit create verb above.
        if any(word in message for word in ("投递", "申请记录")):
            return AgentDecision("tool_call", "list_applications", {})
        if any(word in message for word in ("求职报告", "作战报告", "阶段总结")):
            return AgentDecision("tool_call", "generate_career_report", {})
        if any(word in message for word in ("面试题", "来一道题", "练习面试")):
            return AgentDecision("tool_call", "get_interview_question", {})
        if any(word in message for word in ("薪资", "工资", "待遇")):
            return AgentDecision("tool_call", "evaluate_salary", {})
        if any(word in lowered for word in ("你好", "您好", "嗨", "hello")):
            return AgentDecision(
                "final",
                message=(
                    "本地规则模式：我可以结合已保存的简历、面试和投递数据，"
                    "按固定模板帮你推进下一步求职行动。"
                ),
            )
        return AgentDecision(
            "final",
            message=(
                "当前未配置大模型 API，正在使用本地模板和规则模式，不会进行模型生成。"
                "我可以执行简历查询、岗位匹配、面试题、投递看板和求职报告等本地任务。"
            ),
        )

    def _start_career_action(self, action_type: str, message: str) -> AgentDecision:
        slots = {"action_type": action_type, "arguments": {}}
        slots["arguments"].update(self._extract_action_arguments(action_type, message))
        return self._proposal_or_question(slots)

    def _continue_career_action(self, slots: dict, message: str) -> AgentDecision:
        action_type = slots.get("action_type")
        if action_type not in {
            "set_career_goal", "create_opportunity", "create_action_item",
            "update_opportunity", "create_resume_version",
        }:
            return AgentDecision(
                "final", message="本地规则模式：待继续任务无效，请重新描述要创建的内容。"
            )
        existing = slots.get("arguments") if isinstance(slots.get("arguments"), dict) else {}
        merged = self._merge_action_arguments(
            action_type, existing, self._extract_action_arguments(action_type, message)
        )
        return self._proposal_or_question(
            {"action_type": action_type, "arguments": merged}
        )

    @staticmethod
    def _explicit_action_type(message: str) -> str | None:
        if _NON_WRITE_REQUEST.search(message):
            return None
        goal_command = (
            _POLITE_PREFIX
            + r"(?:(?:设置|保存|记录)(?:我的)?(?:职业|求职)?目标|"
              r"把(?:我的)?(?:职业|求职)?目标)(?:为|是|设为|改成|更新为|[:：])?"
        )
        if re.search(goal_command, message):
            return "set_career_goal"
        if re.search(
            _POLITE_PREFIX
            + r"(?:记录|创建|新增)(?:一个|一条)?(?:新的)?(?:投递|求职机会|申请记录)",
            message,
        ):
            return "create_opportunity"
        if re.search(
            _POLITE_PREFIX + r"(?:记录|创建|新增)(?:一个|一条)?(?:行动项|待办)",
            message,
        ):
            return "create_action_item"
        if re.search(
            _POLITE_PREFIX
            + r"把(?:投递|机会|申请)\s*(?:ID|id|编号)?\s*\d+.*(?:推进到|更新为|改成|设为)",
            message,
        ):
            return "update_opportunity"
        if re.search(
            _POLITE_PREFIX + r"(?:记录|创建|新增)(?:一个|一条)?(?:新)?简历版本",
            message,
        ):
            return "create_resume_version"
        return None

    def _proposal_or_question(self, slots: dict) -> AgentDecision:
        missing = self._missing_fields(slots["action_type"], slots["arguments"])
        if missing:
            labels = {
                "target_role": "目标岗位",
                "company": "公司名称",
                "job_title": "岗位名称",
                "title": "行动项标题",
                "opportunity_id": "投递机会编号",
                "status": "新阶段",
                "resume_id": "源简历编号",
                "content": "新版本正文",
            }
            requested = "、".join(labels[item] for item in missing)
            return AgentDecision(
                "needs_input",
                arguments={"task_type": "career_action", "slots": slots},
                message=f"本地规则模式：请补充{requested}。我只会生成待确认操作，不会直接执行。",
            )
        return AgentDecision(
            "tool_call",
            "propose_career_action",
            {
                "action_type": slots["action_type"],
                "arguments": slots["arguments"],
                "rationale": "根据用户明确提供的信息生成待确认操作",
            },
        )

    @staticmethod
    def _missing_fields(action_type: str, arguments: dict) -> list[str]:
        required = {
            "set_career_goal": ("target_role",),
            "create_opportunity": ("company", "job_title"),
            "create_action_item": ("title",),
            "update_opportunity": ("opportunity_id", "status"),
            "create_resume_version": ("resume_id", "content"),
        }[action_type]
        return [
            field
            for field in required
            if not (
                arguments.get(field)
                if field != "status"
                else (arguments.get("changes") or {}).get("status")
            )
        ]

    @staticmethod
    def _merge_action_arguments(
        action_type: str, existing: dict, extracted: dict
    ) -> dict:
        merged = dict(existing)
        if action_type == "update_opportunity":
            old_changes = existing.get("changes") if isinstance(existing.get("changes"), dict) else {}
            new_changes = extracted.get("changes") if isinstance(extracted.get("changes"), dict) else {}
            merged.update({key: value for key, value in extracted.items() if key != "changes"})
            merged["changes"] = {**old_changes, **new_changes}
        else:
            merged.update(extracted)
        return merged

    @staticmethod
    def _extract_action_arguments(action_type: str, message: str) -> dict:
        if action_type == "set_career_goal":
            role = LocalPolicy._capture(
                message, r"(?:职业目标|求职目标|我的目标|目标岗位|目标职位)(?:是|为|设为|[:：])?\s*([^，,。；;\n]+)"
            )
            return {"target_role": role} if role else {}
        if action_type == "create_opportunity":
            result = {}
            company = LocalPolicy._capture(
                message, r"(?:公司(?:是|为|[:：])?|投递到)\s*([^，,。；;\s]+)"
            )
            job_title = LocalPolicy._capture(
                message, r"(?:岗位|职位)(?:是|为|[:：])?\s*([^，,。；;\n]+)"
            )
            if company:
                result["company"] = company
            if job_title:
                result["job_title"] = job_title
            return result
        if action_type == "create_action_item":
            title = LocalPolicy._capture(
                message, r"(?:行动项|待办)(?:是|为|[:：])?\s*([^，,。；;\n]+)"
            )
            return {"title": title} if title else {}
        if action_type == "update_opportunity":
            result = {}
            opportunity_id = LocalPolicy._capture(
                message, r"(?:投递|机会|申请)(?:ID|id|编号)?\s*[#：:]?\s*(\d+)"
            )
            if opportunity_id:
                result["opportunity_id"] = int(opportunity_id)
            status = next((item for item in _APPLICATION_STATUSES if item in message), None)
            if status:
                result["changes"] = {"status": status}
            return result
        if action_type == "create_resume_version":
            result = {"metadata": {}}
            resume_id = LocalPolicy._capture(
                message, r"(?:简历|源简历)(?:ID|id|编号)?\s*[#：:]?\s*(\d+)"
            )
            content = LocalPolicy._capture(message, r"(?:内容|正文)\s*[:：]\s*(.+)", re.S)
            if resume_id:
                result["resume_id"] = int(resume_id)
            if content:
                result["content"] = content
            return result
        return {}

    @staticmethod
    def _capture(message: str, pattern: str, flags: int = 0) -> str:
        match = re.search(pattern, message, flags)
        return match.group(1).strip() if match else ""

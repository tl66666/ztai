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
        message = state.user_message.strip()
        intent = self._read_intent(message)
        if state.active_task and state.active_task.get("task_type") == "resume_workflow":
            return self._continue_resume_workflow(state)
        if state.observations:
            return self._continue_read_intent(intent, state.observations)

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

        lowered = message.lower()
        action_type = self._explicit_action_type(message)
        if action_type:
            return self._start_career_action(action_type, message)

        if "简历" in message and any(
            word in message for word in ("刚才", "这个岗位", "目标岗位", "岗位看看")
        ):
            remembered_role = re.search(
                r"目标岗位(?:是|为|设为)?\s*(.+?)(?:\s*->|[，,。；;\n]|$)",
                state.context_prompt,
            ) or re.search(
                r'"?target_role"?\s*[:：]\s*"?([^"\n,}]+)',
                state.context_prompt,
            )
            if remembered_role:
                return AgentDecision(
                    "tool_call",
                    "match_job",
                    {"job_title": remembered_role.group(1).strip()},
                )

        if intent in {"career_diagnosis", "guided_start"}:
            return AgentDecision("tool_call", "get_dashboard", {})
        if intent == "capabilities":
            return AgentDecision("final", message=self._capability_message())
        if intent == "opportunities":
            return AgentDecision("tool_call", "list_applications", {})
        if intent == "interview_readiness":
            return AgentDecision("tool_call", "get_dashboard", {})
        if intent in {"resume_analysis", "resume_revision"}:
            return AgentDecision("tool_call", "list_resumes", {})

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
            message=self._fallback_message(),
        )

    @staticmethod
    def _read_intent(message: str) -> str:
        if any(
            phrase in message
            for phrase in (
                "带我开始", "带我使用", "帮我上手", "从哪里开始", "新用户",
                "刚开始找工作", "使用这个求职系统", "求职流程",
            )
        ):
            return "guided_start"
        if any(
            phrase in message
            for phrase in (
                "你能做什么", "可以做什么", "能帮我什么", "有哪些能力",
                "功能介绍", "怎么使用", "如何使用",
            )
        ):
            return "capabilities"
        if any(
            phrase in message
            for phrase in (
                "下一步该做什么", "下一步做什么", "下一步怎么办",
                "分析现在的求职", "分析我的求职", "求职情况",
                "求职诊断", "整体分析", "现在该做什么",
            )
        ):
            return "career_diagnosis"
        if (
            any(word in message for word in ("机会", "申请", "投递"))
            and any(
                word in message
                for word in ("看看", "哪些", "现在", "进展", "情况", "状态", "盘点")
            )
        ):
            return "opportunities"
        if (
            "面试" in message
            and any(
                word in message
                for word in ("准备", "怎么样", "如何", "状态", "进度", "复盘", "水平")
            )
        ):
            return "interview_readiness"
        if "简历" in message:
            if any(word in message for word in ("优化", "修改", "完善", "改写", "生成版本", "新版本")):
                return "resume_revision"
            if any(word in message for word in ("问题", "诊断", "分析", "评估")):
                return "resume_analysis"
        return ""

    def _continue_read_intent(
        self, intent: str, observations: list[dict]
    ) -> AgentDecision:
        observed = {item.get("tool") for item in observations}
        plans = {
            "career_diagnosis": (
                "get_dashboard",
                "get_career_profile",
                "list_action_items",
                "get_training_insights",
            ),
            "guided_start": (
                "get_dashboard",
                "get_career_profile",
                "list_action_items",
                "get_training_insights",
            ),
            "interview_readiness": ("get_dashboard", "get_training_insights"),
            "opportunities": ("list_applications",),
            "resume_analysis": ("list_resumes",),
            "resume_revision": ("list_resumes",),
        }
        plan = plans.get(intent, ())
        next_tool = next((tool for tool in plan if tool not in observed), "")
        if next_tool:
            return AgentDecision("tool_call", next_tool, {})
        if intent in {"career_diagnosis", "guided_start"}:
            reply = self._synthesize_career_diagnosis(observations)
            if intent == "guided_start":
                reply = "我会按当前数据带你走完最短可用路径。\n" + reply
            return AgentDecision(
                "final",
                arguments={"suggested_actions": self._career_guidance_actions(observations)},
                message=reply,
            )
        if intent == "interview_readiness":
            return AgentDecision(
                "final", message=self._synthesize_interview_readiness(observations)
            )
        if intent == "opportunities":
            return AgentDecision(
                "final", message=self._synthesize_opportunities(observations)
            )
        if intent in {"resume_analysis", "resume_revision"}:
            resumes = self._observation_data(observations, "list_resumes", [])
            return self._resume_picker_decision(intent, resumes)
        latest = observations[-1]
        return AgentDecision(
            "final", message=f"本地规则模式：{latest.get('display_text') or '任务已处理。'}"
        )

    @staticmethod
    def _resume_picker_decision(workflow: str, resumes: list[dict]) -> AgentDecision:
        options = []
        for item in resumes if isinstance(resumes, list) else []:
            resume_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(resume_id, int) or resume_id <= 0:
                continue
            options.append({
                "id": resume_id,
                "label": str(item.get("title") or f"简历 #{resume_id}")[:100],
                "preview": str(item.get("preview") or "")[:180],
            })
        if not options:
            return AgentDecision(
                "final",
                message="还没有可用简历。请先在简历实验室保存一份简历，再让 Agent 做诊断或生成优化版本。",
            )
        workflow_label = "优化草稿" if workflow == "resume_revision" else "诊断"
        return AgentDecision(
            "needs_input",
            arguments={
                "task_type": "resume_workflow",
                "slots": {"workflow": workflow, "stage": "select_resume"},
                "input_request": {
                    "kind": "resume_select",
                    "workflow": "revision" if workflow == "resume_revision" else "analysis",
                    "prompt": f"选择要进行{workflow_label}的简历",
                    "options": options,
                },
            },
            message=f"我找到了 {len(options)} 份简历。请选择一份，我会先读取正文，再完成{workflow_label}。",
        )

    def _continue_resume_workflow(self, state) -> AgentDecision:
        slots = state.active_task.get("slots") or {}
        workflow = slots.get("workflow")
        if workflow not in {"resume_analysis", "resume_revision"}:
            return AgentDecision("final", message="简历任务状态无效，请重新发起诊断或优化请求。")
        resume_id = self._selected_resume_id(state.user_message) or slots.get("resume_id")
        if not isinstance(resume_id, int) or resume_id <= 0:
            return AgentDecision(
                "needs_input",
                arguments={
                    "task_type": "resume_workflow",
                    "slots": slots,
                    "input_request": {
                        "kind": "resume_select",
                        "workflow": "revision" if workflow == "resume_revision" else "analysis",
                        "prompt": "请选择一份已保存的简历",
                        "options": [],
                    },
                },
                message="请从上面的简历列表中选择一份，或发送“选择简历 #编号”。",
            )
        observed = {item.get("tool") for item in state.observations}
        if workflow == "resume_analysis":
            if "diagnose_resume" not in observed:
                return AgentDecision("tool_call", "diagnose_resume", {"resume_id": resume_id})
            return AgentDecision("final", message=self._synthesize_resume_advice(state.observations))
        if "prepare_resume_revision" not in observed:
            return AgentDecision("tool_call", "prepare_resume_revision", {"resume_id": resume_id})
        prepared = self._observation_data(state.observations, "prepare_resume_revision", {})
        if not isinstance(prepared, dict) or not prepared.get("content"):
            return AgentDecision("final", message="无法生成可靠的简历草稿，原始简历没有被修改。请检查简历内容后重试。")
        if "propose_career_action" not in observed:
            return AgentDecision(
                "tool_call",
                "propose_career_action",
                {
                    "action_type": "create_resume_version",
                    "arguments": {
                        "resume_id": prepared["resume_id"],
                        "content": prepared["content"],
                        "metadata": prepared["metadata"],
                    },
                    "rationale": "根据用户选择的简历生成可编辑的新版本草稿",
                },
            )
        mode = "模型定向改写" if prepared.get("mode") == "model" else "本地事实保真草稿"
        changes = "；".join(str(item) for item in prepared.get("changes", [])[:3])
        return AgentDecision(
            "final",
            message=(
                f"已生成{mode}并创建待确认版本。{changes}。"
                "请打开草稿预览，按需编辑正文；确认后才会保存为一份新简历，原简历不会被覆盖。"
            ),
        )

    @staticmethod
    def _selected_resume_id(message: str) -> int | None:
        match = re.search(r"(?:选择\s*)?(?:简历\s*)?[#＃]?(\d+)", str(message or ""))
        if not match:
            return None
        value = int(match.group(1))
        return value if value > 0 else None

    @staticmethod
    def _observation_data(observations: list[dict], tool: str, default):
        item = next((row for row in observations if row.get("tool") == tool), None)
        if not item or not item.get("ok"):
            return default
        return item.get("data") if item.get("data") is not None else default

    def _synthesize_career_diagnosis(self, observations: list[dict]) -> str:
        dashboard = self._observation_data(observations, "get_dashboard", {})
        profile = self._observation_data(observations, "get_career_profile", {})
        actions = self._observation_data(observations, "list_action_items", [])
        training = self._observation_data(observations, "get_training_insights", {})
        readiness = dashboard.get("readiness") or {}
        target = profile.get("target_role") or "尚未设置目标岗位"
        cities = profile.get("cities") if isinstance(profile.get("cities"), list) else []
        city = "、".join(str(item) for item in cities[:3] if item) or "城市未设置"
        interview_count = (training.get("interviews") or {}).get("completed_count", 0)
        first_action = next(
            (item.get("title") for item in actions if item.get("status") != "done"), ""
        )
        priorities = []
        if not profile.get("target_role"):
            priorities.append("先明确一个目标岗位和目标城市，后续匹配与建议才有统一基准。")
        if dashboard.get("resumes", 0) == 0:
            priorities.append("先保存一份可投递简历，再做岗位匹配和针对性优化。")
        elif dashboard.get("matches", 0) == 0:
            priorities.append("选择一个真实 JD 做匹配，补齐简历中的核心技能与项目证据。")
        if interview_count == 0:
            priorities.append("完成一次面试训练并记录复盘，先建立可追踪的表达基线。")
        if first_action:
            priorities.append(f"推进现有行动项“{first_action}”，完成后再新增任务。")
        if dashboard.get("applications", 0) == 0:
            priorities.append("建立首个求职机会，记录岗位、阶段和下一次跟进时间。")
        else:
            priorities.append("检查已投递机会的停留阶段，为超过预期未推进的机会安排跟进。")
        priorities = priorities[:3] or ["保持当前节奏，并在每次投递或面试后更新记录与复盘。"]
        priority_text = "\n".join(
            f"优先级 {index}：{text}" for index, text in enumerate(priorities, 1)
        )
        return (
            "本地求职 Agent（无需 API Key）已读取你的业务数据并完成诊断。\n"
            f"现状：准备度 {readiness.get('score', 0)}（{readiness.get('label', '待评估')}），"
            f"简历 {dashboard.get('resumes', 0)} 份，匹配 {dashboard.get('matches', 0)} 次，"
            f"投递 {dashboard.get('applications', 0)} 个，面试训练 {interview_count} 次。\n"
            f"目标：{target} / {city}。\n{priority_text}\n"
            "说明：这是基于本地数据和确定性规则生成的行动排序，不会冒充大模型推理。"
        )

    def _career_guidance_actions(self, observations: list[dict]) -> list[dict[str, str]]:
        dashboard = self._observation_data(observations, "get_dashboard", {})
        profile = self._observation_data(observations, "get_career_profile", {})
        training = self._observation_data(observations, "get_training_insights", {})
        actions = []

        if not profile.get("target_role"):
            actions.append({"label": "完善求职目标", "page": "home", "module": ""})
        if dashboard.get("resumes", 0) == 0:
            actions.append({"label": "录入第一份简历", "page": "resume", "module": "input"})
        elif dashboard.get("matches", 0) == 0:
            actions.append({"label": "粘贴 JD 做匹配", "page": "resume", "module": "jd"})
            actions.append({"label": "先诊断当前简历", "page": "resume", "module": "analysis"})
        else:
            interviews = (training.get("interviews") or {}).get("completed_count", 0)
            if interviews == 0:
                actions.append({"label": "开始模拟面试", "page": "interview", "module": "mock"})
            if dashboard.get("applications", 0) == 0:
                actions.append({"label": "记录第一条投递", "page": "tracker", "module": "add"})
            else:
                actions.append({"label": "查看投递看板", "page": "tracker", "module": "board"})
        return actions[:3]

    def _synthesize_interview_readiness(self, observations: list[dict]) -> str:
        dashboard = self._observation_data(observations, "get_dashboard", {})
        training = self._observation_data(observations, "get_training_insights", {})
        interviews = (training.get("interviews") or {}).get("completed_count", 0)
        practice = (training.get("practice") or {}).get("completed_count", 0)
        audio = (training.get("audio") or {}).get("completed_count", 0)
        if interviews == 0:
            advice = "当前缺少完整面试训练记录。先完成一次模拟面试，再针对低分问题做二次回答。"
        elif audio == 0:
            advice = "已有训练记录，但缺少语音表达证据。下一步补一次限时语音回答，检查结构和节奏。"
        else:
            advice = "已有多类训练证据。下一步围绕目标岗位做专项题，并复盘最近一次薄弱项。"
        return (
            "本地求职 Agent 面试准备诊断："
            f"完整面试训练 {interviews} 次，题库训练 {practice} 次，语音训练 {audio} 次；"
            f"系统累计面试记录 {dashboard.get('interviews', 0)} 条。\n下一步：{advice}"
        )

    def _synthesize_opportunities(self, observations: list[dict]) -> str:
        applications = self._observation_data(observations, "list_applications", [])
        if not applications:
            return (
                "本地求职 Agent 机会盘点：当前还没有投递记录。"
                "建议先录入 1 个真实岗位，至少填写公司、岗位和当前阶段，再安排下一次跟进。"
            )
        stage_counts = {}
        for item in applications:
            status = item.get("status") or "未标记"
            stage_counts[status] = stage_counts.get(status, 0) + 1
        stages = "、".join(f"{name} {count} 个" for name, count in stage_counts.items())
        recent = applications[0]
        return (
            f"本地求职 Agent 机会盘点：共 {len(applications)} 个机会，{stages}。\n"
            f"最近机会：{recent.get('company', '未知公司')} / "
            f"{recent.get('job_title', '未知岗位')} / {recent.get('status', '未标记')}。\n"
            "下一步：优先处理临近面试或长期未推进的机会，并为每个活跃机会设置明确跟进动作。"
        )

    @staticmethod
    def _synthesize_resume_advice(observations: list[dict]) -> str:
        item = next(
            (row for row in observations if row.get("tool") in {"diagnose_resume", "analyze_resume"}), {}
        )
        if item.get("ok") and item.get("display_text"):
            return (
                "本地求职 Agent 简历诊断：\n"
                f"{item['display_text']}\n"
                "建议按“目标岗位关键词 → 项目职责 → 可量化结果”顺序修改，并另存为新版本。"
            )
        return (
            "本地求职 Agent 暂未找到可分析的简历。先保存一份简历，然后重点检查："
            "目标岗位关键词是否出现、项目职责是否具体、结果是否有数字或可验证证据。"
        )

    @staticmethod
    def _capability_message() -> str:
        return (
            "我是本地求职 Agent，无需 API Key 也能执行这些确定性任务：\n"
            "1. 求职诊断：读取准备度、职业目标、行动项和训练记录，给出下一步优先级。\n"
            "2. 简历与岗位：查询或诊断简历、做岗位匹配、分析 JD。\n"
            "3. 面试训练：出题、评估回答、汇总面试与语音训练进度。\n"
            "4. 投递管理：盘点机会阶段、生成求职报告和跟进建议。\n"
            "5. 安全行动：所有写入操作只生成预览，必须由你在操作卡片中确认。\n"
            "配置大模型 API 后可处理更开放的表达；未配置时不会伪装成模型生成。"
        )

    @staticmethod
    def _fallback_message() -> str:
        return (
            "我现在使用本地求职 Agent 模式。这个模式不做开放式大模型生成，"
            "但能读取你的本地求职数据并完成固定任务。\n"
            "可以直接这样问：\n"
            "- 帮我分析现在的求职情况，下一步做什么\n"
            "- 看看我的机会和投递进展\n"
            "- 面试准备得怎么样\n"
            "- 帮我优化简历\n"
            "- 给我一道人岗匹配或面试训练任务"
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

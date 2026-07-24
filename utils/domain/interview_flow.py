from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any


class InterviewFlow:
    """Own interview questions and answer evaluation behind one small interface."""

    def __init__(
        self,
        profiles: Mapping[str, dict[str, Any]],
        *,
        normalize_profile: Callable[[str | None], str],
        voice_analyzer: Callable[[str, float | None], dict[str, Any]],
    ):
        self._profiles = profiles
        self._normalize_profile = normalize_profile
        self._voice_analyzer = voice_analyzer

    def build_stages(self, session: dict[str, Any]) -> list[tuple[str, str]]:
        job_title = session["job_title"]
        profile_key = self._normalize_profile(session.get("career_profile"))
        profile = self._profiles[profile_key]
        ability_names = list(profile["abilities"].keys())
        if profile_key == "tech":
            professional_question = (
                f"如果你来测试/建设 {job_title} 相关系统，"
                "你会如何设计核心用例和接口验证？"
            )
        else:
            professional_question = (
                f"围绕 {job_title}，请讲讲你会如何处理一个典型的"
                f"{ability_names[0]}任务，并说明判断结果好坏的指标。"
            )
        return [
            (
                "resume_deep_dive",
                "我看到你简历里有相关经历。请展开讲一个最能体现你适合"
                f"{profile['label']}方向的经历，按 STAR 结构回答。",
            ),
            ("professional", professional_question),
            (
                "behavioral",
                "讲一次你发现问题并推动解决的经历，你做了什么，结果怎样？",
            ),
            (
                "candidate_questions",
                f"现在进入反问环节。面对{profile['interviewer']}，"
                "你会问哪两个能体现你认真了解岗位的问题？",
            ),
            ("finished", "面试结束。系统已生成综合反馈。"),
        ]

    def evaluate_answer(
        self,
        session: dict[str, Any],
        answer: str,
        duration_seconds: float | None,
        stage: str,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        answer_intent = self.detect_answer_intent(answer)
        voice = self._voice_analyzer(answer, duration_seconds)
        skipped = answer_intent in {"skip", "too_short"}
        if skipped:
            voice["overall_score"] = 0
            voice["dimension_scores"] = {
                "表达流畅": 0,
                "结构逻辑": 0,
                "岗位相关": 0,
                "信息密度": 0,
            }
            feedback = self.skipped_feedback(session["job_title"], stage)
        else:
            feedback = {
                "score": voice["overall_score"],
                "summary": self.answer_summary(
                    answer, voice, session["job_title"]
                ),
                "voice": voice,
                "suggestions": voice["tips"],
                "answer_upgrade": self.answer_upgrade(
                    answer, session["job_title"]
                ),
            }
        candidate = {"role": "candidate", "content": answer, "voice": voice}
        return candidate, feedback, skipped

    @staticmethod
    def detect_answer_intent(answer: str) -> str:
        text = re.sub(r"\s+", "", (answer or "").lower())
        if not text:
            return "empty"
        skip_words = (
            "不知道",
            "不会",
            "不清楚",
            "没想好",
            "下一题",
            "跳过",
            "pass",
            "next",
            "不会答",
        )
        if any(word in text for word in skip_words):
            return "skip"
        if len(text) < 8:
            return "too_short"
        return "answer"

    def skipped_feedback(
        self, job_title: str, stage_name: str = "本题"
    ) -> dict[str, Any]:
        voice = self._voice_analyzer("不知道", None)
        voice["overall_score"] = 0
        voice["dimension_scores"] = {
            "表达流畅": 0,
            "结构逻辑": 0,
            "岗位相关": 0,
            "信息密度": 0,
        }
        return {
            "score": 0,
            "summary": (
                f"你选择跳过{stage_name}。这在练习里可以，但真实面试不能只说"
                "不知道。建议先给一个诚实回应，再说你的补救思路。"
            ),
            "voice": voice,
            "suggestions": [
                "可用话术：这个点我现在不能完整回答，但我会先确认概念，再结合项目场景补充验证。",
                "遇到不会的题，至少说出你知道的边界、排查路径或学习计划。",
                "系统已进入下一题/下一阶段，不会把跳过内容包装成虚假能力。",
            ],
            "answer_upgrade": (
                "保底回答：这个问题我还需要补充学习。面向 "
                f"{job_title}，我会从岗位要求出发，先查清概念，再用项目里的"
                "真实场景做验证和复盘。"
            ),
        }

    @staticmethod
    def answer_upgrade(answer: str, job_title: str) -> str:
        del answer
        return (
            f"可升级表达：面向 {job_title}，我在项目中不仅参与实现/测试，"
            "还围绕核心业务流程设计验证方案。例如在 AI 求职辅助系统中，我覆盖"
            "了简历上传、JD 匹配、模拟面试和投递看板等流程，通过接口测试、"
            "异常场景和回归验证保证系统稳定，并把测试结论沉淀成报告。"
        )

    @staticmethod
    def answer_summary(
        answer: str, voice: dict[str, Any], job_title: str
    ) -> str:
        if len(answer) < 60:
            return (
                f"回答偏短。面试 {job_title} 时，需要把“做过什么、怎么做、"
                "结果如何”讲完整。"
            )
        if voice["structure_score"] < 2:
            return (
                "内容有素材，但结构不够明显。建议先给结论，再按背景、行动、"
                "结果展开。"
            )
        if voice["filler_count"] > 2:
            return (
                "信息量可以，但口头禅偏多。建议用短暂停顿替代"
                "“然后、就是、那个”。"
            )
        return (
            "回答整体可用，已经具备项目证据。下一步重点补充量化指标和岗位关键词。"
        )

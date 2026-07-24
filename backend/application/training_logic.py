from __future__ import annotations

# Long Chinese product copy is intentionally kept intact to preserve response contracts.
# ruff: noqa: E501
import re
from typing import Any

from utils.ai_client import extract_keywords
from utils.domain.interview_flow import InterviewFlow

from .resume_analysis import CAREER_PROFILES, select_career_profile

_QUESTION_BANK = {
    "general": [
        {
            "question": "请做一个 2 分钟自我介绍。",
            "answer": "用 当前身份 + 目标岗位 + 1 个核心项目 + 2 个能力证据 + 求职动机 收束。",
        },
        {
            "question": "你为什么选择这个岗位？",
            "answer": "从兴趣、能力匹配、项目经历、长期成长四点回答。",
        },
        {
            "question": "你有什么问题想问我？",
            "answer": "问岗位挑战、团队技术栈、入职前三个月期待，避免一上来只问福利。",
        },
        {
            "question": "你最大的优势是什么？",
            "answer": "选择与岗位相关的优势，用项目证据支撑，例如测试细致、学习快、能推动问题闭环。",
        },
        {
            "question": "你最大的缺点是什么？",
            "answer": "选择非致命缺点，说明改进动作和结果，不要说与岗位核心能力冲突的缺点。",
        },
    ],
    "test": [
        {
            "question": "如何设计 Web 系统的测试用例？",
            "answer": "按业务流程、输入边界、异常场景、权限、兼容性、性能和接口契约拆分。",
        },
        {
            "question": "接口测试重点关注什么？",
            "answer": "关注状态码、响应结构、业务字段、幂等性、鉴权、异常参数和数据一致性。",
        },
        {
            "question": "JMeter 性能测试怎么看结果？",
            "answer": "看吞吐量、平均/中位/P95 响应时间、错误率、资源瓶颈和并发拐点。",
        },
        {
            "question": "发现一个偶现 bug 你怎么处理？",
            "answer": "先记录环境和复现路径，再补日志、缩小变量、固定数据、提高复现概率，最后给出证据链。",
        },
        {
            "question": "自动化测试适合覆盖哪些场景？",
            "answer": "适合稳定、高频、回归成本高的主流程，不适合频繁变化和强视觉主观判断场景。",
        },
    ],
    "frontend": [
        {
            "question": "如何提升前端页面可用性？",
            "answer": "从信息架构、操作反馈、加载状态、表单校验、响应式和无障碍入手。",
        },
        {
            "question": "前端如何处理接口异常？",
            "answer": "区分网络错误、业务错误、超时和空数据，给出可恢复操作和明确提示。",
        },
    ],
    "python": [
        {
            "question": "Flask 项目如何组织接口？",
            "answer": "按业务模块拆分路由、服务逻辑、数据访问和配置，统一错误处理与响应结构。",
        },
        {
            "question": "SQLite 在小型项目里适合什么场景？",
            "answer": "适合课程项目、单机演示和轻量数据存储，部署简单，但高并发和复杂权限场景应换 MySQL/PostgreSQL。",
        },
    ],
    "ai": [
        {
            "question": "多模型接入为什么要做本地兜底？",
            "answer": "因为 API Key、网络、限流都可能失败，本地兜底能保证核心流程可演示、可测试、可用。",
        },
        {
            "question": "AI Agent 和普通聊天接口有什么区别？",
            "answer": "Agent 需要有目标、上下文、工具调用和流程状态，不只是单轮问答。",
        },
    ],
}


class TrainingLogic:
    """Pure interview coaching policy shared by training and interview modules."""

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return CAREER_PROFILES

    def analyze_voice(
        self,
        answer: str,
        duration_seconds: float | str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean = answer.strip()
        chinese = len(re.findall(r"[\u4e00-\u9fa5]", clean))
        words = re.findall(r"[A-Za-z]+", clean)
        units = chinese + len(words)
        duration = max(float(duration_seconds or 0), units / 3.2, 20)
        speed = round(units / duration * 60)
        fillers = ("嗯", "呃", "啊", "然后", "就是", "那个", "这个", "的话", "其实", "可能")
        filler_detail = {word: clean.count(word) for word in fillers if clean.count(word)}
        filler_count = sum(filler_detail.values())
        markers = ("首先", "其次", "最后", "背景", "任务", "行动", "结果", "因为", "所以")
        structure_score = sum(marker in clean for marker in markers)
        tips = []
        if speed > 260:
            tips.append("语速偏快，建议关键经历处主动停顿 0.5 秒，让面试官跟上信息。")
        elif speed < 140:
            tips.append("语速偏慢，可以提前准备 2 分钟版本，减少犹豫停顿。")
        else:
            tips.append("语速处在较自然区间，继续保持。")
        if filler_count > 2:
            tips.append(f"口头禅出现 {filler_count} 次，优先减少“然后、就是、那个”。")
        if structure_score < 2:
            tips.append("结构感不足，建议使用 STAR 或“背景-行动-结果”组织答案。")
        if units < 60:
            tips.append("回答略短，需要补充具体项目细节和量化结果。")
        audio_metrics = metrics or {}
        audio_quality = "未提供真实音频，仅按文本估算表达表现。"
        if audio_metrics:
            audio_parts = []
            silence_ratio = float(audio_metrics.get("silence_ratio") or 0)
            clipping_ratio = float(audio_metrics.get("clipping_ratio") or 0)
            average_volume = float(audio_metrics.get("average_volume") or 0)
            if silence_ratio > 0.55:
                audio_parts.append("停顿偏多，像在临时组织语言")
                tips.append("录音停顿比例偏高，建议提前准备“结论-证据-结果”三句骨架。")
            elif silence_ratio < 0.15:
                audio_parts.append("停顿较少，表达连贯但要注意给面试官消化时间")
            else:
                audio_parts.append("停顿比例较自然")
            if clipping_ratio > 0.02:
                audio_parts.append("存在爆音/过载")
                tips.append("录音出现爆音，正式面试前调整麦克风距离和系统音量。")
            if average_volume and average_volume < 0.025:
                audio_parts.append("音量偏小，面试时可能听不清")
                tips.append("音量偏小，建议提高麦克风增益或靠近一点。")
            elif average_volume > 0.22:
                audio_parts.append("音量偏大，注意不要贴麦")
            audio_quality = "；".join(audio_parts)
        keyword_hits = [
            word
            for word in ("项目", "测试", "接口", "自动化", "性能", "结果", "推动", "优化", "用户")
            if word in clean
        ]
        return {
            "overall_score": max(
                35, min(95, 82 - filler_count * 4 + structure_score * 3 - abs(speed - 200) // 12)
            ),
            "estimated_speech_rate": speed,
            "pace_label": "偏快" if speed > 260 else ("偏慢" if speed < 140 else "自然"),
            "filler_count": filler_count,
            "filler_ratio": round(filler_count / max(1, units) * 100, 2),
            "filler_detail": filler_detail,
            "structure_score": structure_score,
            "keyword_hits": keyword_hits,
            "clarity": "清晰" if structure_score >= 2 else "需要加强",
            "audio_quality": audio_quality,
            "audio_metrics": audio_metrics,
            "dimension_scores": {
                "表达流畅": max(40, min(95, 90 - filler_count * 6)),
                "结构逻辑": max(35, min(95, 55 + structure_score * 10)),
                "岗位相关": max(35, min(95, 50 + len(keyword_hits) * 7)),
                "信息密度": max(35, min(95, min(90, units))),
            },
            "tips": tips,
        }

    def select_profile(self, body: dict[str, Any], *, text: str = "") -> str:
        return select_career_profile(body, text=text, job_title=str(body.get("job_title") or ""))

    def question_bank(self) -> dict[str, list[dict[str, str]]]:
        bank = {key: list(value) for key, value in _QUESTION_BANK.items()}
        for key, profile in CAREER_PROFILES.items():
            if key == "tech":
                continue
            bank[key] = [
                {
                    "question": f"请结合真实经历说明你的{ability}能力。",
                    "answer": f"使用 STAR 结构，说明{ability}任务、方法、协作对象和结果。",
                }
                for ability in profile["abilities"]
            ]
        return bank

    def project_questions(self, category: str, job_title: str, level: str) -> list[dict[str, str]]:
        del level
        if category in CAREER_PROFILES and category != "tech":
            profile = CAREER_PROFILES[category]
            return [
                {
                    "question": f"如果你入职{job_title}，前三周你会如何拆解工作目标并证明自己能上手？",
                    "reference": "先确认岗位核心任务和评价标准，再拆成学习资料、业务流程、工具熟悉、协作对象和第一批可交付成果，最后用数据或交付物复盘。",
                    "focus": f"{profile['label']} · 入职适应",
                    "difficulty": "真实场景",
                },
                {
                    "question": f"请结合一个经历说明你为什么适合{job_title}，不要泛泛说性格好。",
                    "reference": "用 STAR 结构说明背景、任务、行动和结果，重点突出岗位相关能力、工具方法、协作对象和可量化结果。",
                    "focus": f"{profile['interviewer']}追问",
                    "difficulty": "经历深挖",
                },
            ]
        return self._technical_project_questions(category, job_title)

    def answer_intent(self, answer: str) -> str:
        return InterviewFlow.detect_answer_intent(answer)

    def sample_answer(self, question: str, category: str) -> str:
        del question
        if category in CAREER_PROFILES and category != "tech":
            profile = CAREER_PROFILES[category]
            ability = next(iter(profile["abilities"]))
            return f"参考回答：我会先给结论，再用一个和{profile['label']}相关的经历说明。比如在一次任务中，我负责{ability}相关工作，先确认目标和评价标准，再拆解执行步骤、同步协作对象，最后用数据、交付物或反馈证明结果。"
        if category == "test":
            return "参考回答：我会先确认需求和核心业务流程，再从正常流程、边界值、异常输入、权限、接口契约、兼容性和性能几个维度设计用例。执行时会记录实际结果、缺陷复现步骤和优先级，最后通过回归测试确认问题闭环。"
        if category == "ai":
            return "参考回答：AI Agent 不只是单轮聊天，它需要明确目标、保存上下文、按流程推进任务，并在模型不可用时有兜底策略。比如本项目把简历、JD、面试状态和语音分析串起来，形成完整求职辅助流程。"
        if category == "python":
            return "参考回答：后端项目可以按路由、业务逻辑、数据访问和配置拆分。接口层负责参数校验和响应，应用层处理业务规则，数据层负责持久化，同时统一错误处理，方便测试和维护。"
        return "参考回答：我会先给结论，再用一个真实项目举例说明背景、我的行动和结果，最后回到岗位要求，说明这段经历为什么能证明我适合这个岗位。"

    def answer_upgrade(self, answer: str, job_title: str) -> str:
        return InterviewFlow.answer_upgrade(answer, job_title)

    def keywords(self, answer: str) -> list[str]:
        return extract_keywords(answer)

    def follow_up(self, question: str, category: str) -> str:
        del question
        if category in CAREER_PROFILES and category != "tech":
            return "追问：请把这个回答再补充一个真实经历，说明你当时用了什么方法、和谁协作、最后产生了什么结果。"
        return {
            "test": "追问：如果这个功能上线后出现偶发失败，你如何定位是前端、后端、数据库还是模型接口问题？",
            "ai": "追问：如果模型返回不符合预期，你会如何通过 prompt、规则校验和兜底策略保证产品可用？",
            "python": "追问：这个接口如果并发访问变多，你会从哪些指标判断瓶颈？",
            "frontend": "追问：移动端和桌面端布局差异较大时，你如何做断点和视觉回归验证？",
        }.get(category, "追问：请把这个回答再结合一个真实项目经历讲一遍，重点说你的个人贡献。")

    @staticmethod
    def _technical_project_questions(category: str, job_title: str) -> list[dict[str, str]]:
        if category == "test":
            return [
                {
                    "question": f"如果让你测试一个 {job_title} 相关的 AI Web 系统，你会如何拆分测试范围？",
                    "reference": "可以从核心业务流程、接口契约、文件上传解析、模型异常兜底、权限和兼容性几个维度拆分，并说明优先级。",
                    "focus": "测试设计能力",
                    "difficulty": "项目场景",
                },
                {
                    "question": "模型接口偶发超时或返回格式不稳定，你会怎么设计验证和兜底方案？",
                    "reference": "回答要覆盖超时重试、错误提示、本地规则兜底、日志记录、接口 Mock、边界用例和回归验证。",
                    "focus": "异常处理",
                    "difficulty": "实战追问",
                },
            ]
        if category == "ai":
            return [
                {
                    "question": "你怎么理解 AI Agent 和普通聊天机器人的区别？结合本项目说明。",
                    "reference": "Agent 应有目标、状态、工具/数据调用和任务推进。本项目可举简历、JD、面试、投递数据联动的例子。",
                    "focus": "Agent 理解",
                    "difficulty": "项目深挖",
                }
            ]
        if category == "python":
            return [
                {
                    "question": "FastAPI 项目里你会如何划分路由、应用逻辑和数据访问？",
                    "reference": "说明接口层负责参数和响应，应用层负责业务，数据层负责持久化；再补充错误处理和测试策略。",
                    "focus": "后端结构",
                    "difficulty": "基础到实战",
                }
            ]
        return [
            {
                "question": "前端页面如何保证复杂表单、结果区和模块切换不混乱？",
                "reference": "可以从状态管理、模块过滤、输入校验、结果复用、响应式布局和用户下一步引导回答。",
                "focus": "前端工程",
                "difficulty": "项目场景",
            }
        ]

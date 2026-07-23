from __future__ import annotations

import json
from typing import Any, BinaryIO

from backend.adapters.legacy_training import LegacyTrainingLogic
from backend.adapters.persistence import TrainingRepository
from backend.adapters.training_audio import LocalTrainingAudioStorage


class TrainingModule:
    """Application use cases for interview practice, audio, and history."""

    def __init__(
        self,
        repository: TrainingRepository,
        audio_storage: LocalTrainingAudioStorage,
        logic: LegacyTrainingLogic,
        *,
        local_user_id: int,
    ):
        self._repository = repository
        self._audio_storage = audio_storage
        self._logic = logic
        self._local_user_id = int(local_user_id)

    def analyze_voice(self, body: dict[str, Any]) -> dict[str, Any]:
        answer = str(body.get("answer") or "")
        if not answer:
            raise ValueError("请先输入或录入回答内容")
        return {
            "success": True,
            **self._logic.analyze_voice(
                answer,
                body.get("duration_seconds"),
                body.get("audio_metrics"),
            ),
        }

    def analyze_audio(
        self,
        *,
        transcript: str,
        duration_seconds: str | None,
        metrics_json: str,
        requested_user_id: str | None,
        audio: BinaryIO | None,
        audio_name: str,
    ) -> dict[str, Any]:
        self._require_local_user(requested_user_id)
        clean_transcript = transcript.strip()
        if not clean_transcript:
            raise ValueError("请提供录音对应的转写文本")
        try:
            parsed_metrics = json.loads(metrics_json or "{}")
        except json.JSONDecodeError:
            parsed_metrics = {}
        metrics = parsed_metrics if isinstance(parsed_metrics, dict) else {}
        saved_name = (
            self._audio_storage.store(audio, audio_name)
            if audio is not None and audio_name
            else ""
        )
        result = self._logic.analyze_voice(
            clean_transcript,
            duration_seconds,
            metrics,
        )
        result["summary"] = self._audio_summary(result, saved_name)
        self._repository.save_audio(
            self._local_user_id,
            transcript=clean_transcript,
            audio_file=saved_name,
            score=int(result.get("overall_score") or 0),
            metrics=metrics,
            feedback=result,
        )
        return {"success": True, "audio_file": saved_name, **result}

    def professional_pack(self, body: dict[str, Any]) -> dict[str, Any]:
        category = str(body.get("category") or "test")
        profile_key = self._logic.select_profile(body)
        if category == "career":
            category = profile_key
        level = str(body.get("level") or "campus")
        job_title = str(body.get("job_title") or "目标岗位")
        bank = self._logic.question_bank()
        base_questions = bank.get(category, bank["general"])
        level_name = {
            "campus": "校招基础",
            "junior": "初级实战",
            "project": "项目深挖",
        }.get(level, "校招基础")
        questions = [
            {
                "question": item["question"],
                "reference": item["answer"],
                "focus": f"{job_title} · {category}",
                "difficulty": level_name,
            }
            for item in base_questions[:5]
        ]
        questions.extend(
            self._logic.project_questions(category, job_title, level)
        )
        profile = self._logic.profiles[profile_key]
        return {
            "success": True,
            "category": category,
            "level": level,
            "profile": {
                "id": profile_key,
                "label": profile["label"],
                "interviewer": profile["interviewer"],
            },
            "questions": questions[:8],
        }

    def practice_feedback(self, body: dict[str, Any]) -> dict[str, Any]:
        self._require_local_user(body.get("user_id"))
        question = str(body.get("question") or "").strip()
        answer = str(body.get("answer") or "").strip()
        category = str(body.get("category") or "general")
        profile_key = self._logic.select_profile(body, text=answer)
        if category == "career":
            category = profile_key
        if not question or not answer:
            raise ValueError("题目和回答不能为空")

        if self._logic.answer_intent(answer) in {"skip", "too_short"}:
            result = {
                "success": True,
                "score": 0,
                "category": category,
                "question": question,
                "dimension_scores": {
                    "专业性": 0,
                    "结构化": 0,
                    "完整度": 0,
                    "表达": 0,
                },
                "hits": [],
                "problems": ["本题没有形成有效回答，系统不会编造评分。"],
                "sample_answer": self._logic.sample_answer(question, category),
                "upgrade": "不会的问题建议诚实说明边界，再补一个排查思路或学习计划。",
                "follow_up": "下一步：先看参考答案，再用自己的项目经历重答一遍。",
                "needs_answer": True,
            }
            self._save_practice(category, question, answer, result)
            return result

        voice = self._logic.analyze_voice(answer)
        technical_terms = self._logic.keywords(answer)
        structure_hit = any(
            word in answer
            for word in ("首先", "其次", "最后", "背景", "任务", "行动", "结果", "因此")
        )
        score = int(voice["overall_score"])
        if category in {"test", "python", "frontend", "ai"} or (
            category in self._logic.profiles
        ):
            score = min(96, score + min(12, len(technical_terms) * 3))
        if not structure_hit:
            score = max(35, score - 8)
        result = {
            "success": True,
            "score": score,
            "category": category,
            "profile": {
                "id": profile_key,
                "label": self._logic.profiles[profile_key]["label"],
            },
            "question": question,
            "dimension_scores": {
                "专业性": min(95, 48 + len(technical_terms) * 8),
                "结构化": 86 if structure_hit else 55,
                "完整度": min(95, 40 + len(answer) // 3),
                "表达": voice["dimension_scores"]["表达流畅"],
            },
            "hits": technical_terms,
            "problems": [
                item
                for item in (
                    None
                    if structure_hit
                    else "回答缺少清晰结构，建议使用“结论-步骤-结果”。",
                    None if len(answer) >= 80 else "回答偏短，需要补充例子或项目经历。",
                    None
                    if technical_terms
                    else "专业关键词较少，建议加入工具、方法或指标。",
                )
                if item
            ],
            "sample_answer": self._logic.sample_answer(question, category),
            "upgrade": self._logic.answer_upgrade(
                answer,
                str(body.get("job_title") or "目标岗位"),
            ),
            "follow_up": self._logic.follow_up(question, category),
        }
        self._save_practice(category, question, answer, result)
        return result

    def list_records(self, user_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        return {"success": True, **self._repository.list_all(user_id)}

    def delete_record(self, record_type: str, record_id: int) -> dict[str, Any]:
        row = self._repository.get_record(
            record_type,
            record_id,
            self._local_user_id,
        )
        if row is None:
            raise LookupError("记录不存在")
        if record_type == "audio" and row.get("audio_file"):
            self._audio_storage.delete(str(row["audio_file"]))
        self._repository.delete_record(
            record_type,
            record_id,
            self._local_user_id,
        )
        return {"success": True, "message": "记录已删除"}

    def clear_records(self, user_id: int) -> dict[str, Any]:
        self._require_local_user(user_id)
        for audio_file in self._repository.audio_files(user_id):
            self._audio_storage.delete(audio_file)
        self._repository.clear(user_id)
        return {"success": True, "message": "训练记录已清空"}

    def _save_practice(
        self,
        category: str,
        question: str,
        answer: str,
        result: dict[str, Any],
    ) -> None:
        self._repository.save_practice(
            self._local_user_id,
            category=category,
            question=question,
            answer=answer,
            score=int(result.get("score") or 0),
            feedback=result,
        )

    def _require_local_user(self, value: object) -> None:
        if value is not None and int(value) != self._local_user_id:
            raise PermissionError("Access denied")

    @staticmethod
    def _audio_summary(result: dict[str, Any], saved_name: str) -> str:
        metrics = result.get("audio_metrics") or {}
        file_note = (
            "已保存录音，可用于复盘。"
            if saved_name
            else "未保存音频文件，仅使用浏览器侧音频指标。"
        )
        return (
            f"{file_note} 本次语速为 {result['estimated_speech_rate']} 字/分钟，"
            f"停顿比例约 {round(float(metrics.get('silence_ratio') or 0) * 100)}%，"
            f"口头禅 {result['filler_count']} 次。建议重点关注："
            f"{result['audio_quality']}"
        )

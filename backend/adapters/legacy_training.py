from __future__ import annotations

from typing import Any


class LegacyTrainingLogic:
    """Temporary pure-logic bridge while interview content leaves app.py."""

    def __init__(self, legacy_module: Any):
        self._legacy = legacy_module

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return self._legacy.CAREER_PROFILES

    def analyze_voice(
        self,
        answer: str,
        duration_seconds: float | str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._legacy.analyze_voice_text(answer, duration_seconds, metrics)

    def select_profile(self, body: dict[str, Any], *, text: str = "") -> str:
        return self._legacy.select_career_profile(
            body,
            text=text,
            job_title=body.get("job_title", ""),
        )

    def question_bank(self) -> dict[str, list[dict[str, str]]]:
        return self._legacy.extended_question_bank()

    def project_questions(
        self,
        category: str,
        job_title: str,
        level: str,
    ) -> list[dict[str, str]]:
        return self._legacy.build_project_followup_questions(
            category,
            job_title,
            level,
        )

    def answer_intent(self, answer: str) -> str:
        return self._legacy.detect_answer_intent(answer)

    def sample_answer(self, question: str, category: str) -> str:
        return self._legacy.build_sample_practice_answer(question, category)

    def answer_upgrade(self, answer: str, job_title: str) -> str:
        return self._legacy.build_answer_upgrade(answer, job_title)

    def keywords(self, answer: str) -> list[str]:
        return self._legacy.extract_keywords(answer)

    def follow_up(self, question: str, category: str) -> str:
        return self._legacy.build_follow_up_question(question, category)

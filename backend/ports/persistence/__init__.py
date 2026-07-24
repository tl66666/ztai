from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Any, Protocol, Self

Record = dict[str, Any]


class ResumeRepository(Protocol):
    def add(
        self,
        user_id: int,
        *,
        title: str,
        content: str,
        file_path: str | None = None,
        file_type: str | None = None,
        analysis_result: str | None = None,
        tailored_result: str | None = None,
    ) -> int: ...

    def list_owned(self, user_id: int) -> list[Record]: ...

    def get_owned(self, resume_id: int, user_id: int) -> Record | None: ...

    def replace_upload(
        self,
        resume_id: int,
        user_id: int,
        *,
        file_path: str,
        file_type: str,
        content: str,
    ) -> bool: ...

    def update_text(
        self,
        resume_id: int,
        user_id: int,
        *,
        title: str,
        content: str,
    ) -> bool: ...

    def delete_owned(self, resume_id: int, user_id: int) -> bool: ...

    def set_analysis(self, resume_id: int, user_id: int, analysis: str) -> bool: ...

    def set_tailored(self, resume_id: int, user_id: int, tailored: str) -> bool: ...


class CareerInsightsRepository(Protocol):
    def dashboard_evidence(self, user_id: int) -> Record: ...

    def report_evidence(self, user_id: int) -> Record: ...

    def coaching_evidence(self, user_id: int) -> Record: ...


class OpportunityWorkspaceRepository(Protocol):
    def snapshot(
        self,
        user_id: int,
        *,
        opportunity_id: int,
        resume_id: int | None,
    ) -> Record: ...

    def owned_active_exists(self, opportunity_id: int, user_id: int) -> bool: ...

    def add_match(
        self,
        user_id: int,
        *,
        resume_id: int,
        job_title: str,
        match_score: int,
        analysis: str,
        jd_text: str,
        details_json: str,
        application_id: int | None,
    ) -> int: ...


class AgentContextRepository(Protocol):
    def context_entities_exist(
        self,
        user_id: int,
        *,
        resume_id: int | None = None,
        opportunity_id: int | None = None,
    ) -> bool: ...


class TrainingRepository(Protocol):
    def save_audio(
        self,
        user_id: int,
        *,
        transcript: str,
        audio_file: str,
        score: int,
        metrics: Record,
        feedback: Record,
    ) -> None: ...

    def save_practice(
        self,
        user_id: int,
        *,
        category: str,
        question: str,
        answer: str,
        score: int,
        feedback: Record,
    ) -> None: ...

    def list_all(self, user_id: int) -> dict[str, list[Record]]: ...

    def get_record(self, record_type: str, record_id: int, user_id: int) -> Record | None: ...

    def delete_record(self, record_type: str, record_id: int, user_id: int) -> None: ...

    def audio_files(self, user_id: int) -> list[str]: ...

    def clear(self, user_id: int) -> None: ...


class UnitOfWork(Protocol):
    resumes: ResumeRepository
    career_insights: CareerInsightsRepository
    opportunities: OpportunityWorkspaceRepository
    agent_context: AgentContextRepository
    training: TrainingRepository
    career: Any
    events: Any
    interviews: Any

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]

__all__ = [
    "AgentContextRepository",
    "CareerInsightsRepository",
    "OpportunityWorkspaceRepository",
    "Record",
    "ResumeRepository",
    "TrainingRepository",
    "UnitOfWork",
    "UnitOfWorkFactory",
]

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict

from backend.api.http import domain_error_response
from backend.application.training import TrainingModule


class VoiceAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    answer: str = ""
    duration_seconds: float | None = None
    audio_metrics: dict[str, Any] | None = None


class ProfessionalPackRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    category: str = "test"
    career_profile: str | None = None
    profile: str | None = None
    level: str = "campus"
    job_title: str = "目标岗位"


class PracticeFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: int | None = None
    question: str = ""
    answer: str = ""
    category: str = "general"
    career_profile: str | None = None
    profile: str | None = None
    job_title: str = ""


def create_training_router(
    module_provider: Callable[[], TrainingModule],
) -> APIRouter:
    router = APIRouter(tags=["interview-training"])

    @router.post("/api/interview/analyze-voice")
    def analyze_voice(body: VoiceAnalysisRequest):
        return _invoke(module_provider().analyze_voice, body.model_dump())

    @router.post("/api/interview/analyze-audio")
    async def analyze_audio(
        transcript: str = Form(""),
        duration_seconds: str | None = Form(None),
        metrics: str = Form("{}"),
        user_id: str | None = Form(None),
        audio: UploadFile | None = File(None),
    ):
        return _invoke(
            module_provider().analyze_audio,
            transcript=transcript,
            duration_seconds=duration_seconds,
            metrics_json=metrics,
            requested_user_id=user_id,
            audio=audio.file if audio else None,
            audio_name=audio.filename or "" if audio else "",
        )

    @router.post("/api/interview/professional-pack")
    def professional_pack(body: ProfessionalPackRequest):
        return _invoke(module_provider().professional_pack, body.model_dump())

    @router.post("/api/interview/practice-feedback")
    def practice_feedback(body: PracticeFeedbackRequest):
        return _invoke(module_provider().practice_feedback, body.model_dump())

    @router.get("/api/training-records/{user_id}")
    def list_records(user_id: int):
        return _invoke(module_provider().list_records, user_id)

    @router.delete("/api/training-records/{user_id}/clear")
    def clear_records(user_id: int):
        return _invoke(module_provider().clear_records, user_id)

    @router.delete("/api/training-records/{record_type}/{record_id}")
    def delete_record(record_type: str, record_id: int):
        return _invoke(module_provider().delete_record, record_type, record_id)

    return router


def _invoke(operation: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any):
    try:
        return operation(*args, **kwargs)
    except (PermissionError, LookupError, ValueError) as exc:
        return domain_error_response(exc)

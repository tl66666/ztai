from __future__ import annotations

from backend.adapters.legacy_flask import LegacyFlaskAdapter
from backend.adapters.persistence import TrainingRepository
from backend.adapters.storage import LocalBlobStorage
from backend.adapters.training_audio import LocalTrainingAudioStorage
from backend.core.settings import Settings

from .career import CareerModule
from .career_insights import CareerInsightsModule
from .interviews import InterviewModule
from .opportunities import OpportunityModule
from .resume_intelligence import ResumeIntelligenceModule
from .resumes import ResumeModule
from .training import TrainingModule


class ApplicationContainer:
    """Own runtime-scoped adapters and application modules for one ASGI instance."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.legacy = LegacyFlaskAdapter(settings)
        self._interviews: InterviewModule | None = None
        self._career: CareerModule | None = None
        self._career_insights: CareerInsightsModule | None = None
        self._opportunities: OpportunityModule | None = None
        self._resumes: ResumeModule | None = None
        self._resume_intelligence: ResumeIntelligenceModule | None = None
        self._training: TrainingModule | None = None

    def initialize(self) -> None:
        self.legacy.initialize()

    def database_ready(self) -> bool:
        return self.legacy.database_ready()

    @property
    def career(self) -> CareerModule:
        if self._career is None:
            self._career = CareerModule(
                self.legacy.career_service,
                local_user_id=self.legacy.local_user_id,
            )
        return self._career

    @property
    def career_insights(self) -> CareerInsightsModule:
        if self._career_insights is None:
            self._career_insights = CareerInsightsModule(
                self.settings.db_path,
                self.legacy.career_service,
                self.legacy.ai_client_manager.get_ai_client,
                local_user_id=self.legacy.local_user_id,
            )
        return self._career_insights

    @property
    def interviews(self) -> InterviewModule:
        if self._interviews is None:
            self._interviews = InterviewModule(
                self.legacy.interview_service,
                local_user_id=self.legacy.local_user_id,
            )
        return self._interviews

    @property
    def opportunities(self) -> OpportunityModule:
        if self._opportunities is None:
            self._opportunities = OpportunityModule(
                self.legacy.career_service,
                self.settings.db_path,
                local_user_id=self.legacy.local_user_id,
            )
        return self._opportunities

    @property
    def resumes(self) -> ResumeModule:
        if self._resumes is None:
            self._resumes = ResumeModule(
                self.settings.db_path,
                LocalBlobStorage(
                    self.settings.upload_folder,
                    max_bytes=self.settings.max_upload_bytes,
                ),
                self.settings.export_folder,
                local_user_id=self.legacy.local_user_id,
            )
        return self._resumes

    @property
    def resume_intelligence(self) -> ResumeIntelligenceModule:
        if self._resume_intelligence is None:
            self._resume_intelligence = ResumeIntelligenceModule(
                self.settings.db_path,
                self.legacy.ai_client_manager.get_ai_client,
                local_user_id=self.legacy.local_user_id,
            )
        return self._resume_intelligence

    @property
    def training(self) -> TrainingModule:
        if self._training is None:
            self._training = TrainingModule(
                TrainingRepository(self.settings.db_path),
                LocalTrainingAudioStorage(
                    self.settings.upload_folder,
                    max_bytes=self.settings.max_upload_bytes,
                ),
                self.legacy.training_logic,
                local_user_id=self.legacy.local_user_id,
            )
        return self._training

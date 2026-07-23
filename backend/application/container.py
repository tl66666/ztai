from __future__ import annotations

from backend.adapters.persistence import AgentRepository, TrainingRepository
from backend.adapters.storage import LocalBlobStorage
from backend.adapters.training_audio import LocalTrainingAudioStorage
from backend.core.runtime import RuntimeDatabase
from backend.core.settings import Settings
from utils.ai_client import AIClientManager
from utils.domain import CareerService, InterviewService
from utils.domain.interview_flow import InterviewFlow

from .agent import AgentModule
from .career import CareerModule
from .career_insights import CareerInsightsModule
from .interviews import InterviewModule
from .opportunities import OpportunityModule
from .platform import FileUtilityModule, RuntimeConfigModule
from .resume_analysis import (
    CAREER_PROFILES,
    normalize_career_profile,
    select_career_profile,
)
from .resume_intelligence import ResumeIntelligenceModule
from .resumes import ResumeModule
from .training import TrainingModule
from .training_logic import TrainingLogic


class ApplicationContainer:
    """Own runtime-scoped adapters and application modules for one ASGI instance."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.local_user_id = settings.local_user_id
        ai_config_path = (
            settings.ai_config_path or settings.db_path.parent / "runtime" / "ai-config.json"
        )
        self.ai_clients = AIClientManager(ai_config_path)
        self.runtime_database = RuntimeDatabase(
            settings.db_path,
            upload_folder=settings.upload_folder,
            export_folder=settings.export_folder,
            local_user_id=self.local_user_id,
        )
        self.training_logic = TrainingLogic()
        self._career_service: CareerService | None = None
        self._interview_service: InterviewService | None = None
        self._agent: AgentModule | None = None
        self._interviews: InterviewModule | None = None
        self._career: CareerModule | None = None
        self._career_insights: CareerInsightsModule | None = None
        self._opportunities: OpportunityModule | None = None
        self._resumes: ResumeModule | None = None
        self._resume_intelligence: ResumeIntelligenceModule | None = None
        self._training: TrainingModule | None = None
        self._runtime_config: RuntimeConfigModule | None = None
        self._file_utilities: FileUtilityModule | None = None

    def initialize(self) -> None:
        self.runtime_database.initialize()

    def database_ready(self) -> bool:
        return self.runtime_database.ready()

    @property
    def career_service(self) -> CareerService:
        if self._career_service is None:
            self._career_service = CareerService(
                self.settings.db_path,
                local_user_id=self.local_user_id,
            )
        return self._career_service

    @property
    def interview_service(self) -> InterviewService:
        if self._interview_service is None:
            flow = InterviewFlow(
                CAREER_PROFILES,
                normalize_profile=normalize_career_profile,
                voice_analyzer=self.training_logic.analyze_voice,
            )
            self._interview_service = InterviewService(
                self.settings.db_path,
                local_user_id=self.local_user_id,
                stages_builder=flow.build_stages,
                answer_evaluator=flow.evaluate_answer,
                profile_selector=lambda profile, resume, job: select_career_profile(
                    {"career_profile": profile} if profile else {},
                    text=resume,
                    job_title=job,
                ),
                profile_resolver=lambda profile: {
                    "id": normalize_career_profile(profile),
                    "label": CAREER_PROFILES[normalize_career_profile(profile)][
                        "label"
                    ],
                    "interviewer": CAREER_PROFILES[
                        normalize_career_profile(profile)
                    ]["interviewer"],
                },
                completion_summary=(
                    "整体流程完成。建议把自我介绍压缩到 120 秒内，并准备 "
                    "2 个项目深挖版本、1 个问题定位案例和 1 个团队协作案例。"
                ),
            )
        return self._interview_service

    @property
    def agent(self) -> AgentModule:
        if self._agent is None:
            from utils.agent_runtime.actions import ActionProposalService
            from utils.agent_runtime.service import AgentService

            local_user_id = self.local_user_id
            self._agent = AgentModule(
                AgentService(
                    str(self.settings.db_path),
                    ai_client_provider=self.ai_clients.get_ai_client,
                ),
                ActionProposalService(
                    self.settings.db_path,
                    career_service=self.career_service,
                    local_user_id=local_user_id,
                ),
                AgentRepository(self.settings.db_path),
                local_user_id=local_user_id,
                allowed_origins=self.settings.allowed_origins,
            )
        return self._agent

    @property
    def career(self) -> CareerModule:
        if self._career is None:
            self._career = CareerModule(
                self.career_service,
                local_user_id=self.local_user_id,
            )
        return self._career

    @property
    def career_insights(self) -> CareerInsightsModule:
        if self._career_insights is None:
            self._career_insights = CareerInsightsModule(
                self.settings.db_path,
                self.career_service,
                self.ai_clients.get_ai_client,
                local_user_id=self.local_user_id,
            )
        return self._career_insights

    @property
    def interviews(self) -> InterviewModule:
        if self._interviews is None:
            self._interviews = InterviewModule(
                self.interview_service,
                local_user_id=self.local_user_id,
            )
        return self._interviews

    @property
    def opportunities(self) -> OpportunityModule:
        if self._opportunities is None:
            self._opportunities = OpportunityModule(
                self.career_service,
                self.settings.db_path,
                local_user_id=self.local_user_id,
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
                local_user_id=self.local_user_id,
            )
        return self._resumes

    @property
    def resume_intelligence(self) -> ResumeIntelligenceModule:
        if self._resume_intelligence is None:
            self._resume_intelligence = ResumeIntelligenceModule(
                self.settings.db_path,
                self.ai_clients.get_ai_client,
                local_user_id=self.local_user_id,
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
                self.training_logic,
                local_user_id=self.local_user_id,
            )
        return self._training

    @property
    def runtime_config(self) -> RuntimeConfigModule:
        if self._runtime_config is None:
            self._runtime_config = RuntimeConfigModule(
                self.ai_clients,
                self.training_logic,
            )
        return self._runtime_config

    @property
    def file_utilities(self) -> FileUtilityModule:
        if self._file_utilities is None:
            self._file_utilities = FileUtilityModule(
                self.settings.upload_folder,
                self.settings.export_folder,
                max_upload_bytes=self.settings.max_upload_bytes,
            )
        return self._file_utilities

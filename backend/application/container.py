from __future__ import annotations

from backend.adapters.legacy_flask import LegacyFlaskAdapter
from backend.adapters.storage import LocalBlobStorage
from backend.core.settings import Settings

from .interviews import InterviewModule
from .opportunities import OpportunityModule
from .resumes import ResumeModule


class ApplicationContainer:
    """Own runtime-scoped adapters and application modules for one ASGI instance."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.legacy = LegacyFlaskAdapter(settings)
        self._interviews: InterviewModule | None = None
        self._opportunities: OpportunityModule | None = None
        self._resumes: ResumeModule | None = None

    def initialize(self) -> None:
        self.legacy.initialize()

    def database_ready(self) -> bool:
        return self.legacy.database_ready()

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

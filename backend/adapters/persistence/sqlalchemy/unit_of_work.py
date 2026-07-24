from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from .agent_repository import SqlAlchemyAgentContextRepository
from .career_repository import SqlAlchemyCareerRepository
from .event_repository import SqlAlchemyEventRepository
from .insights_repository import SqlAlchemyCareerInsightsRepository
from .interview_repository import SqlAlchemyInterviewRepository
from .opportunity_repository import SqlAlchemyOpportunityWorkspaceRepository
from .resume_repository import SqlAlchemyResumeRepository
from .training_repository import SqlAlchemyTrainingRepository


class SqlAlchemyUnitOfWork:
    """One transaction and one identity map for an application use case."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self.resumes = SqlAlchemyResumeRepository(session)
        self.career_insights = SqlAlchemyCareerInsightsRepository(session)
        self.opportunities = SqlAlchemyOpportunityWorkspaceRepository(session)
        self.agent_context = SqlAlchemyAgentContextRepository(session)
        self.events = SqlAlchemyEventRepository(session)
        self.career = SqlAlchemyCareerRepository(session, self.events)
        self.interviews = SqlAlchemyInterviewRepository(session, self.events)
        self.training = SqlAlchemyTrainingRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

from sqlalchemy import select
from sqlalchemy.orm import Session

from .core_models import job_applications, resumes


class SqlAlchemyAgentContextRepository:
    def __init__(self, session: Session):
        self._session = session

    def context_entities_exist(
        self,
        user_id: int,
        *,
        resume_id: int | None = None,
        opportunity_id: int | None = None,
    ) -> bool:
        if resume_id is not None:
            resume = self._session.execute(
                select(resumes.c.id).where(
                    resumes.c.id == resume_id,
                    resumes.c.user_id == user_id,
                )
            ).first()
            if resume is None:
                return False
        if opportunity_id is not None:
            opportunity = self._session.execute(
                select(job_applications.c.id).where(
                    job_applications.c.id == opportunity_id,
                    job_applications.c.user_id == user_id,
                    job_applications.c.deleted_at.is_(None),
                )
            ).first()
            if opportunity is None:
                return False
        return True

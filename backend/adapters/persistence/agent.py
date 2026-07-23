from __future__ import annotations

import os
from pathlib import Path

from utils.domain.database import connect


class AgentRepository:
    """Persistence adapter for Agent request ownership checks."""

    def __init__(self, db_path: str | os.PathLike[str]):
        self._db_path = Path(db_path)

    def context_entities_exist(
        self,
        user_id: int,
        *,
        resume_id: int | None = None,
        opportunity_id: int | None = None,
    ) -> bool:
        with connect(self._db_path) as connection:
            if resume_id is not None:
                resume = connection.execute(
                    "SELECT 1 FROM resumes WHERE id = ? AND user_id = ?",
                    (resume_id, user_id),
                ).fetchone()
                if resume is None:
                    return False
            if opportunity_id is not None:
                opportunity = connection.execute(
                    """
                    SELECT 1
                    FROM job_applications
                    WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                    """,
                    (opportunity_id, user_id),
                ).fetchone()
                if opportunity is None:
                    return False
        return True

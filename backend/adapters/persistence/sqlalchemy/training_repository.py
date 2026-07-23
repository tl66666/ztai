from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from .training_models import audio_records, interviews, practice_records


class SqlAlchemyTrainingRepository:
    _TABLES = {
        "interview": interviews,
        "practice": practice_records,
        "audio": audio_records,
    }

    def __init__(self, session: Session):
        self._session = session

    def save_audio(
        self,
        user_id: int,
        *,
        transcript: str,
        audio_file: str,
        score: int,
        metrics: dict[str, Any],
        feedback: dict[str, Any],
    ) -> None:
        self._session.execute(
            insert(audio_records).values(
                user_id=user_id,
                transcript=transcript,
                audio_file=audio_file,
                score=score,
                metrics=json.dumps(metrics, ensure_ascii=False),
                feedback=json.dumps(feedback, ensure_ascii=False),
            )
        )

    def save_practice(
        self,
        user_id: int,
        *,
        category: str,
        question: str,
        answer: str,
        score: int,
        feedback: dict[str, Any],
    ) -> None:
        self._session.execute(
            insert(practice_records).values(
                user_id=user_id,
                category=category,
                question=question,
                answer=answer,
                score=score,
                feedback=json.dumps(feedback, ensure_ascii=False),
            )
        )

    def list_all(self, user_id: int) -> dict[str, list[dict[str, Any]]]:
        return {
            "interviews": self._records(
                interviews,
                user_id,
                (
                    interviews.c.id,
                    interviews.c.job_title,
                    interviews.c.conversation,
                    interviews.c.score,
                    interviews.c.feedback,
                    interviews.c.created_at,
                ),
                30,
            ),
            "practices": self._records(
                practice_records,
                user_id,
                (
                    practice_records.c.id,
                    practice_records.c.category,
                    practice_records.c.question,
                    practice_records.c.answer,
                    practice_records.c.score,
                    practice_records.c.feedback,
                    practice_records.c.created_at,
                ),
                50,
            ),
            "audios": self._records(
                audio_records,
                user_id,
                (
                    audio_records.c.id,
                    audio_records.c.transcript,
                    audio_records.c.audio_file,
                    audio_records.c.score,
                    audio_records.c.metrics,
                    audio_records.c.feedback,
                    audio_records.c.created_at,
                ),
                50,
            ),
        }

    def get_record(
        self,
        record_type: str,
        record_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        table = self._table(record_type)
        row = self._session.execute(
            select(table).where(table.c.id == record_id, table.c.user_id == user_id)
        ).mappings().first()
        return dict(row) if row is not None else None

    def delete_record(self, record_type: str, record_id: int, user_id: int) -> None:
        table = self._table(record_type)
        self._session.execute(
            delete(table).where(table.c.id == record_id, table.c.user_id == user_id)
        )

    def audio_files(self, user_id: int) -> list[str]:
        rows = self._session.execute(
            select(audio_records.c.audio_file).where(audio_records.c.user_id == user_id)
        ).scalars()
        return [str(value) for value in rows if value]

    def clear(self, user_id: int) -> None:
        for table in (interviews, practice_records, audio_records):
            self._session.execute(delete(table).where(table.c.user_id == user_id))

    def _records(self, table, user_id: int, columns, limit: int) -> list[dict[str, Any]]:
        statement = (
            select(*columns)
            .where(table.c.user_id == user_id)
            .order_by(table.c.created_at.desc())
            .limit(limit)
        )
        return [dict(row) for row in self._session.execute(statement).mappings()]

    @classmethod
    def _table(cls, record_type: str):
        try:
            return cls._TABLES[record_type]
        except KeyError as exc:
            raise ValueError("记录类型不存在") from exc

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.domain.database import connect


class TrainingRepository:
    """SQLite adapter for interview practice and audio history."""

    _TABLES = {
        "interview": "interviews",
        "practice": "practice_records",
        "audio": "audio_records",
    }

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)

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
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO audio_records
                    (user_id, transcript, audio_file, score, metrics, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    transcript,
                    audio_file,
                    score,
                    json.dumps(metrics, ensure_ascii=False),
                    json.dumps(feedback, ensure_ascii=False),
                ),
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
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO practice_records
                    (user_id, category, question, answer, score, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    category,
                    question,
                    answer,
                    score,
                    json.dumps(feedback, ensure_ascii=False),
                ),
            )

    def list_all(self, user_id: int) -> dict[str, list[dict[str, Any]]]:
        with connect(self._db_path) as connection:
            interviews = connection.execute(
                """
                SELECT id, job_title, conversation, score, feedback, created_at
                FROM interviews
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 30
                """,
                (user_id,),
            ).fetchall()
            practices = connection.execute(
                """
                SELECT id, category, question, answer, score, feedback, created_at
                FROM practice_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id,),
            ).fetchall()
            audios = connection.execute(
                """
                SELECT id, transcript, audio_file, score, metrics, feedback, created_at
                FROM audio_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id,),
            ).fetchall()
        return {
            "interviews": [dict(row) for row in interviews],
            "practices": [dict(row) for row in practices],
            "audios": [dict(row) for row in audios],
        }

    def get_record(
        self,
        record_type: str,
        record_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        table = self._table(record_type)
        with connect(self._db_path) as connection:
            row = connection.execute(
                f'SELECT * FROM "{table}" WHERE id = ? AND user_id = ?',
                (record_id, user_id),
            ).fetchone()
        return dict(row) if row else None

    def delete_record(self, record_type: str, record_id: int, user_id: int) -> None:
        table = self._table(record_type)
        with connect(self._db_path) as connection:
            connection.execute(
                f'DELETE FROM "{table}" WHERE id = ? AND user_id = ?',
                (record_id, user_id),
            )

    def audio_files(self, user_id: int) -> list[str]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT audio_file FROM audio_records WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return [str(row["audio_file"]) for row in rows if row["audio_file"]]

    def clear(self, user_id: int) -> None:
        with connect(self._db_path) as connection:
            connection.execute("DELETE FROM interviews WHERE user_id = ?", (user_id,))
            connection.execute(
                "DELETE FROM practice_records WHERE user_id = ?",
                (user_id,),
            )
            connection.execute(
                "DELETE FROM audio_records WHERE user_id = ?",
                (user_id,),
            )

    @classmethod
    def _table(cls, record_type: str) -> str:
        try:
            return cls._TABLES[record_type]
        except KeyError as exc:
            raise ValueError("记录类型不存在") from exc

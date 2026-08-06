from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application


class TrainingFastAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        )
        self.root = Path(self.temporary_directory.name)
        self.settings = Settings(
            environment="test",
            db_path=self.root / "jobhunter.db",
            upload_folder=self.root / "uploads",
            export_folder=self.root / "exports",
        )
        self.client = TestClient(create_application(self.settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        import gc, shutil
        gc.collect()
        try:
            self.temporary_directory.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temporary_directory.name, ignore_errors=True)

    def test_native_training_flow_preserves_feedback_audio_and_history(self) -> None:
        voice = self.client.post(
            "/api/interview/analyze-voice",
            json={
                "answer": "首先我确认目标，其次执行接口测试，最后复盘结果。",
                "duration_seconds": 30,
            },
        )
        self.assertEqual(voice.status_code, 200)
        self.assertTrue(voice.json()["success"])

        feedback = self.client.post(
            "/api/interview/practice-feedback",
            json={
                "question": "如何测试一个 Web 系统？",
                "answer": (
                    "首先确认核心流程，其次使用接口测试覆盖异常输入，"
                    "最后根据缺陷和回归结果完成复盘。"
                ),
                "category": "test",
            },
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["success"])

        audio = self.client.post(
            "/api/interview/analyze-audio",
            data={
                "transcript": "首先说明背景，然后描述行动，最后给出结果。",
                "duration_seconds": "25",
                "metrics": '{"silence_ratio": 0.2}',
            },
            files={"audio": ("answer.wav", b"RIFF-audio", "audio/wav")},
        )
        self.assertEqual(audio.status_code, 200)
        audio_payload = audio.json()
        self.assertTrue(audio_payload["success"])
        self.assertTrue(audio_payload["audio_file"])
        self.assertTrue(
            (self.settings.upload_folder / audio_payload["audio_file"]).is_file()
        )

        records = self.client.get("/api/training-records/1")
        self.assertEqual(records.status_code, 200)
        payload = records.json()
        self.assertEqual(len(payload["practices"]), 1)
        self.assertEqual(len(payload["audios"]), 1)

        deleted = self.client.delete(
            f"/api/training-records/audio/{payload['audios'][0]['id']}"
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(
            (self.settings.upload_folder / audio_payload["audio_file"]).exists()
        )

    def test_clear_only_removes_the_authenticated_users_records(self) -> None:
        with sqlite3.connect(self.settings.db_path) as connection:
            connection.execute(
                """
                INSERT INTO practice_records
                    (user_id, category, question, answer, score)
                VALUES (1, 'general', 'local', 'answer', 60)
                """
            )
            connection.execute(
                """
                INSERT INTO practice_records
                    (user_id, category, question, answer, score)
                VALUES (2, 'general', 'foreign', 'secret', 70)
                """
            )

        response = self.client.delete("/api/training-records/1/clear")

        self.assertEqual(response.status_code, 200)
        with sqlite3.connect(self.settings.db_path) as connection:
            local_count = connection.execute(
                "SELECT COUNT(*) FROM practice_records WHERE user_id = 1"
            ).fetchone()[0]
            foreign_count = connection.execute(
                "SELECT COUNT(*) FROM practice_records WHERE user_id = 2"
            ).fetchone()[0]
        self.assertEqual(local_count, 0)
        self.assertEqual(foreign_count, 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.settings import Settings
from backend.main import create_application
from utils.agent_runtime.actions import ActionProposalService
from utils.domain import CareerService
from utils.domain.database import connect


class NativeAgentRouterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        )
        root = Path(self.temporary_directory.name)
        self.settings = Settings(
            environment="test",
            db_path=root / "jobhunter.db",
            upload_folder=root / "uploads",
            export_folder=root / "exports",
            allowed_origins=(
                "http://localhost:5000",
                "http://127.0.0.1:5000",
            ),
        )
        self.client_context = TestClient(create_application(self.settings))
        self.client = self.client_context.__enter__()
        self.actions = ActionProposalService(
            self.settings.db_path,
            career_service=CareerService(self.settings.db_path),
            local_user_id=1,
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        import gc, shutil
        gc.collect()
        try:
            self.temporary_directory.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temporary_directory.name, ignore_errors=True)

    def test_conversation_and_chat_contracts_are_native(self):
        created = self.client.post(
            "/api/agent/conversations",
            json={"user_id": 1, "title": "迁移测试"},
        )
        conversation_id = created.json()["conversation"]["id"]
        chatted = self.client.post(
            "/api/agent/chat",
            json={"conversation_id": conversation_id, "message": "你好"},
        )
        messages = self.client.get(
            f"/api/agent/conversations/{conversation_id}/messages?user_id=1"
        )
        openapi = self.client.get("/api/v1/openapi.json").json()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(chatted.status_code, 200)
        self.assertEqual(chatted.json()["conversation_id"], conversation_id)
        self.assertEqual(len(messages.json()["messages"]), 2)
        self.assertIn("/api/agent/chat", openapi["paths"])
        self.assertIn("/api/agent/actions/{proposal_id}/confirm", openapi["paths"])

    def test_chat_rejects_untrusted_input_and_context_entities_before_writes(self):
        invalid = self.client.post(
            "/api/agent/chat",
            json={"user_id": 1, "message": "hello"},
        )
        artifact = self.client.post(
            "/api/agent/chat",
            json={"message": "[object PointerEvent]"},
        )
        with connect(self.settings.db_path) as connection:
            foreign_resume = connection.execute(
                """
                INSERT INTO resumes(user_id, title, content)
                VALUES (2, 'foreign', 'secret')
                """
            ).lastrowid
        foreign = self.client.post(
            "/api/agent/chat",
            json={"message": "hello", "context": {"resume_id": foreign_resume}},
        )

        self.assertEqual(
            invalid.json(),
            {"success": False, "message": "请求只能包含消息、会话和上下文"},
        )
        self.assertEqual(
            artifact.json(),
            {
                "success": False,
                "message": "点击已忽略，请在输入框中写下你的问题后再发送",
            },
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json()["message"], "上下文实体不存在")

    def test_action_workflow_preserves_errors_origin_and_public_redaction(self):
        secret = "secret@example.test private evidence"
        proposal = self.actions.propose(
            1,
            "create_action_item",
            {"title": "Draft", "description": secret},
        )
        fetched = self.client.get(f"/api/agent/actions/{proposal['id']}")
        foreign = self.client.post(
            f"/api/agent/actions/{proposal['id']}/edit",
            json={"title": "blocked"},
            headers={"Origin": "https://evil.example"},
        )
        spoofed = self.client.post(
            f"/api/agent/actions/{proposal['id']}/cancel",
            json={"user_id": 2},
        )
        edited = self.client.post(
            f"/api/agent/actions/{proposal['id']}/edit",
            json={"title": "Final"},
            headers={"Origin": "http://localhost:5000"},
        )
        confirmed = self.client.post(
            f"/api/agent/actions/{proposal['id']}/confirm",
            json={},
            headers={"Origin": "http://localhost:5000"},
        )

        self.assertNotIn(secret, fetched.text)
        self.assertNotIn('"arguments"', fetched.text)
        self.assertEqual(foreign.status_code, 403)
        self.assertEqual(foreign.json()["error"]["code"], "foreign_origin")
        self.assertEqual(spoofed.status_code, 400)
        self.assertEqual(spoofed.json()["error"]["code"], "user_id_not_allowed")
        self.assertEqual(edited.json()["action"]["editable"]["title"], "Final")
        self.assertEqual(confirmed.json()["action"]["status"], "completed")

    def test_clear_endpoints_only_clear_the_owned_conversation(self):
        first = self.client.post(
            "/api/agent/conversations", json={"title": "first"}
        ).json()["conversation"]["id"]
        second = self.client.post(
            "/api/agent/conversations", json={"title": "second"}
        ).json()["conversation"]["id"]
        for conversation_id in (first, second):
            self.client.post(
                "/api/agent/chat",
                json={"conversation_id": conversation_id, "message": "你好"},
            )

        cleared = self.client.post(
            f"/api/agent/conversations/{first}/clear",
            json={"user_id": 1},
        )
        deprecated = self.client.post(
            "/api/agent/clear-memory",
            json={"conversation_id": second, "user_id": 1},
        )

        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(deprecated.status_code, 200)
        for conversation_id in (first, second):
            messages = self.client.get(
                f"/api/agent/conversations/{conversation_id}/messages?user_id=1"
            )
            self.assertEqual(messages.json()["messages"], [])


if __name__ == "__main__":
    unittest.main()

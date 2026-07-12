import os
import tempfile
import unittest
from unittest.mock import patch

import app as app_module


class AgentAPITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = app_module.DB_PATH
        app_module.DB_PATH = os.path.join(self.temp_dir.name, "api.db")
        app_module._agent_service = None
        app_module.init_db()
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module._agent_service = None
        app_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def create_conversation(self, user_id=1, title="新对话"):
        response = self.client.post(
            "/api/agent/conversations",
            json={"user_id": user_id, "title": title},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["conversation"]["id"]

    def messages(self, conversation_id, user_id=1):
        return self.client.get(
            f"/api/agent/conversations/{conversation_id}/messages?user_id={user_id}"
        )

    def test_chat_creates_and_reuses_conversation(self):
        first = self.client.post(
            "/api/agent/chat", json={"user_id": 1, "message": "你好"}
        ).get_json()
        second = self.client.post(
            "/api/agent/chat",
            json={
                "user_id": 1,
                "conversation_id": first["conversation_id"],
                "message": "看我的求职进度",
            },
        ).get_json()

        self.assertTrue(first["success"])
        self.assertEqual(second["conversation_id"], first["conversation_id"])
        self.assertEqual(len(self.messages(first["conversation_id"]).get_json()["messages"]), 4)

    def test_first_message_names_a_precreated_conversation(self):
        conversation_id = self.create_conversation(title="新对话")

        self.client.post(
            "/api/agent/chat",
            json={
                "user_id": 1,
                "conversation_id": conversation_id,
                "message": "准备杭州 Python 测试岗位",
            },
        )

        conversations = self.client.get("/api/agent/conversations/1").get_json()["conversations"]
        title = next(item["title"] for item in conversations if item["id"] == conversation_id)
        self.assertEqual(title, "准备杭州 Python 测试岗位")

    def test_conversation_history_cannot_be_read_by_another_user(self):
        conversation_id = self.create_conversation(user_id=1)
        self.client.post(
            "/api/agent/chat",
            json={"user_id": 1, "conversation_id": conversation_id, "message": "你好"},
        )

        response = self.messages(conversation_id, user_id=2)

        self.assertEqual(response.status_code, 403)

    def test_clear_only_affects_requested_conversation(self):
        first = self.create_conversation()
        second = self.create_conversation()
        for conversation_id in (first, second):
            self.client.post(
                "/api/agent/chat",
                json={"user_id": 1, "conversation_id": conversation_id, "message": "你好"},
            )

        response = self.client.post(
            f"/api/agent/conversations/{first}/clear", json={"user_id": 1}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.messages(first).get_json()["messages"], [])
        self.assertNotEqual(self.messages(second).get_json()["messages"], [])

    def test_list_conversations_returns_only_owned_records(self):
        self.create_conversation(user_id=1, title="我的会话")
        app_module.get_agent_service().store.create_conversation(2, "别人的会话")

        response = self.client.get("/api/agent/conversations/1").get_json()

        self.assertEqual([item["title"] for item in response["conversations"]], ["我的会话"])

    def test_single_user_api_rejects_client_user_impersonation(self):
        create_response = self.client.post(
            "/api/agent/conversations",
            json={"user_id": 2, "title": "冒充会话"},
        )
        chat_response = self.client.post(
            "/api/agent/chat",
            json={"user_id": 2, "message": "读取我的简历"},
        )
        list_response = self.client.get("/api/agent/conversations/2")

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(chat_response.status_code, 403)
        self.assertEqual(list_response.status_code, 403)

    def test_application_tool_suggests_the_existing_tracker_page(self):
        conversation_id = self.create_conversation()

        response = self.client.post(
            "/api/agent/chat",
            json={
                "user_id": 1,
                "conversation_id": conversation_id,
                "message": "查看我的投递记录",
            },
        ).get_json()

        self.assertEqual(response["suggested_actions"][0]["page"], "tracker")

    def test_chat_returns_proposals_and_message_history_restores_cards(self):
        conversation_id = self.create_conversation()
        local_client = type("LocalClient", (), {"api_key": ""})()

        with patch(
            "utils.agent_runtime.service.get_ai_client", return_value=local_client
        ):
            response = self.client.post(
                "/api/agent/chat",
                json={
                    "user_id": 1,
                    "conversation_id": conversation_id,
                    "message": "创建投递，公司是星河科技，岗位是测试工程师",
                },
            ).get_json()

        messages = self.messages(conversation_id).get_json()["messages"]
        assistant = messages[-1]
        self.assertEqual(len(response["action_proposals"]), 1)
        self.assertEqual(
            assistant["metadata"]["action_proposals"], response["action_proposals"]
        )
        self.assertNotEqual(response["action_proposals"], response["suggested_actions"])


if __name__ == "__main__":
    unittest.main()

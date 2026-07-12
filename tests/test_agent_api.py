import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch
from unittest.mock import Mock

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
            "/api/agent/chat", json={"message": "你好"}
        ).get_json()
        second = self.client.post(
            "/api/agent/chat",
            json={
                "conversation_id": first["conversation_id"],
                "message": "看我的求职进度",
            },
        ).get_json()

        self.assertTrue(first["success"])
        self.assertEqual(second["conversation_id"], first["conversation_id"])
        self.assertEqual(len(self.messages(first["conversation_id"]).get_json()["messages"]), 4)

    def test_chat_rejects_invalid_message_lengths_before_writes(self):
        def counts():
            with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
                return tuple(
                    conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("agent_runs", "agent_memories", "agent_messages")
                )

        before = counts()
        for message in ("", "   ", {"not": "text"}, "x" * 12001):
            with self.subTest(kind=type(message).__name__, length=len(message)):
                response = self.client.post(
                    "/api/agent/chat", json={"message": message}
                )
                payload = response.get_json()
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    payload,
                    {"success": False, "message": "消息必须是 1 到 12000 个字符"},
                )
                self.assertNotIn("x" * 100, response.get_data(as_text=True))
        self.assertEqual(counts(), before)

    def test_chat_accepts_only_identifier_context_and_passes_it_to_service(self):
        service = Mock()
        service.chat.return_value = {
            "reply": "ok", "ai_used": False, "conversation_id": "conversation-1",
            "status": "completed", "events": [], "tools_used": [],
            "action_proposals": [], "suggested_actions": [],
        }
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes(user_id,title,content) VALUES (1,'Owned','content')"
            ).lastrowid
            opportunity_id = conn.execute(
                "INSERT INTO job_applications(user_id,company,job_title) VALUES (1,'Owned','Role')"
            ).lastrowid
            conn.commit()
        context = {"module": "resume:jd", "opportunity_id": opportunity_id, "resume_id": resume_id}

        with patch.object(app_module, "get_agent_service", return_value=service):
            response = self.client.post(
                "/api/agent/chat",
                json={"conversation_id": "conversation-1", "message": "分析差距", "context": context},
            )

        self.assertEqual(response.status_code, 200)
        service.chat.assert_called_once_with(
            user_id=1, message="分析差距", conversation_id="conversation-1", context=context
        )

    def test_chat_rejects_client_identity_unknown_fields_and_bad_context_shapes(self):
        invalid_bodies = (
            {"user_id": 1, "message": "hello"},
            {"message": "hello", "unexpected": True},
        )
        for body in invalid_bodies:
            with self.subTest(body=body):
                response = self.client.post("/api/agent/chat", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["message"], "请求只能包含消息、会话和上下文")

        for context in (
            [],
            None,
            "resume:jd",
            {"module": "resume:unknown"},
            {"module": "unknown:page"},
            {"module": "resume:jd:extra"},
        ):
            with self.subTest(context=context):
                response = self.client.post(
                    "/api/agent/chat", json={"message": "hello", "context": context}
                )
                self.assertEqual(response.status_code, 400)
                expected = "上下文模块不存在" if isinstance(context, dict) else "上下文只能包含当前模块和实体 ID"
                self.assertEqual(response.get_json()["message"], expected)

        for context in (
            {"opportunity_id": 1, "company": "untrusted"},
            {"resume_id": 1, "resume_content": "private"},
            {"opportunity_id": "1"},
            {"resume_id": 0},
        ):
            with self.subTest(context=context):
                response = self.client.post(
                    "/api/agent/chat", json={"message": "hello", "context": context}
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["message"], "上下文只能包含当前模块和实体 ID")

    def test_chat_rejects_nonexistent_and_foreign_context_entities(self):
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            foreign_resume = conn.execute(
                "INSERT INTO resumes(user_id,title,content) VALUES (2,'Foreign','content')"
            ).lastrowid
            foreign_opportunity = conn.execute(
                "INSERT INTO job_applications(user_id,company,job_title) VALUES (2,'Foreign','Role')"
            ).lastrowid
            conn.commit()

        for context in (
            {"resume_id": foreign_resume},
            {"opportunity_id": foreign_opportunity},
            {"resume_id": 999999},
            {"opportunity_id": 999999},
        ):
            with self.subTest(context=context):
                response = self.client.post(
                    "/api/agent/chat", json={"message": "hello", "context": context}
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.get_json()["message"], "上下文实体不存在")

    def test_first_message_names_a_precreated_conversation(self):
        conversation_id = self.create_conversation(title="新对话")

        self.client.post(
            "/api/agent/chat",
            json={
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
            json={"conversation_id": conversation_id, "message": "你好"},
        )

        response = self.messages(conversation_id, user_id=2)

        self.assertEqual(response.status_code, 403)

    def test_clear_only_affects_requested_conversation(self):
        first = self.create_conversation()
        second = self.create_conversation()
        for conversation_id in (first, second):
            self.client.post(
                "/api/agent/chat",
                json={"conversation_id": conversation_id, "message": "你好"},
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
        self.assertEqual(chat_response.status_code, 400)
        self.assertEqual(chat_response.get_json()["message"], "请求只能包含消息、会话和上下文")
        self.assertEqual(list_response.status_code, 403)

    def test_application_tool_suggests_the_existing_tracker_page(self):
        conversation_id = self.create_conversation()

        response = self.client.post(
            "/api/agent/chat",
            json={
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

    def test_profile_and_report_result_endpoints_validate_exact_owned_id(self):
        service = app_module.get_career_service()
        profile = service.upsert_profile(1, {"target_role": "Engineer"})
        report = service.save_report(
            1, {"report_type": "weekly", "title": "Week 1", "content": {"summary": "ok"}}
        )
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            foreign_report = conn.execute(
                "INSERT INTO career_reports(user_id,report_type,content_json,status) "
                "VALUES (2,'weekly','{}','ready')"
            ).lastrowid
            conn.commit()

        profile_response = self.client.get(f"/api/profile/{profile['id']}")
        report_response = self.client.get(f"/api/career-reports/{report['id']}")

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.get_json()["data"]["id"], profile["id"])
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.get_json()["data"]["id"], report["id"])
        for path in (
            f"/api/profile/{profile['id'] + 99999}",
            f"/api/career-reports/{foreign_report}",
            "/api/career-reports/999999",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertFalse(response.get_json()["success"])

    def test_profile_and_report_result_endpoints_contain_server_errors(self):
        service = Mock()
        service.get_profile.side_effect = sqlite3.OperationalError("database unavailable")
        service.get_report.side_effect = sqlite3.OperationalError("database unavailable")

        with patch.object(app_module, "get_career_service", return_value=service):
            profile_response = self.client.get("/api/profile/1")
            report_response = self.client.get("/api/career-reports/1")

        self.assertEqual(profile_response.status_code, 500)
        self.assertEqual(report_response.status_code, 500)
        self.assertEqual(profile_response.get_json()["message"], "结果暂时无法读取")
        self.assertEqual(report_response.get_json()["message"], "结果暂时无法读取")


if __name__ == "__main__":
    unittest.main()

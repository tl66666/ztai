import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing
from unittest.mock import patch

from tests.agent_api_client import create_agent_test_runtime


class AgentResumeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.temp_dir.name}/resume-agent.db"
        self.client_context, self.client = create_agent_test_runtime(
            self.temp_dir.name,
            db_name="resume-agent.db",
        )
        self.client_context.__enter__()
        self.container = self.client_context.app.state.container
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.resume_id = conn.execute(
                "INSERT INTO resumes(user_id,title,content) VALUES (1,?,?)",
                (
                    "后端开发简历",
                    "张三\n项目经历\n• 负责 Flask 接口开发\n技能：Python Flask SQLite",
                ),
            ).lastrowid
            conn.execute(
                "INSERT INTO resumes(user_id,title,content) VALUES (1,?,?)",
                ("测试开发简历", "李四\n项目经历\n负责接口测试\n技能：Python Playwright"),
            )
            conn.commit()
        self.container.career_service.upsert_profile(
            1, {"target_role": "Python 后端工程师"}
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        import gc, shutil
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.temp_dir.name, ignore_errors=True)
    def local_client(self):
        return type("LocalClient", (), {"api_key": ""})()

    def local_ai_mode(self):
        client = self.local_client()
        stack = ExitStack()
        stack.enter_context(
            patch("utils.agent_runtime.service.get_ai_client", return_value=client)
        )
        stack.enter_context(
            patch("utils.agent_runtime.tools.get_ai_client", return_value=client)
        )
        return stack

    def test_local_agent_lists_resume_choices_for_revision(self):
        with self.local_ai_mode():
            response = self.client.post(
                "/api/agent/chat", json={"message": "帮我优化简历"}
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "needs_input")
        self.assertEqual(payload["input_request"]["kind"], "resume_select")
        self.assertEqual(payload["input_request"]["workflow"], "revision")
        self.assertEqual(
            [option["id"] for option in payload["input_request"]["options"]],
            [self.resume_id, self.resume_id + 1],
        )

    def test_colloquial_resume_question_prompts_a_resume_choice(self):
        with self.local_ai_mode():
            response = self.client.post(
                "/api/agent/chat", json={"message": "我的简历可以吗"}
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "needs_input")
        self.assertEqual(payload["input_request"]["kind"], "resume_select")
        self.assertEqual(payload["input_request"]["workflow"], "analysis")

    def test_selected_resume_creates_editable_revision_proposal_and_confirms_new_version(self):
        with self.local_ai_mode():
            selection = self.client.post(
                "/api/agent/chat", json={"message": "帮我优化简历"}
            ).get_json()
            created = self.client.post(
                "/api/agent/chat",
                json={
                    "conversation_id": selection["conversation_id"],
                    "message": f"选择简历 #{self.resume_id}",
                },
            ).get_json()

        self.assertEqual(created["status"], "degraded")
        self.assertEqual(len(created["action_proposals"]), 1)
        proposal_id = created["action_proposals"][0]["id"]
        self.assertEqual(created["action_proposals"][0]["action_type"], "create_resume_version")

        draft = self.client.get(f"/api/agent/actions/{proposal_id}/draft")
        self.assertEqual(draft.status_code, 200)
        draft_payload = draft.get_json()
        self.assertIn("求职目标：Python 后端工程师", draft_payload["draft"]["content"])
        self.assertIn("- 负责 Flask 接口开发", draft_payload["draft"]["content"])

        edited = self.client.post(
            f"/api/agent/actions/{proposal_id}/edit",
            json={"content": "张三\n项目经历\n- 完成 Flask 接口开发并通过测试"},
        )
        self.assertEqual(edited.status_code, 200)
        confirmed = self.client.post(
            f"/api/agent/actions/{proposal_id}/confirm", json={}
        )
        self.assertEqual(confirmed.status_code, 200)

        with closing(sqlite3.connect(self.db_path)) as conn:
            source = conn.execute(
                "SELECT content FROM resumes WHERE id = ?", (self.resume_id,)
            ).fetchone()[0]
            saved = conn.execute(
                "SELECT content FROM resumes WHERE id = ?",
                (confirmed.get_json()["result"]["id"],),
            ).fetchone()[0]
        self.assertIn("• 负责 Flask 接口开发", source)
        self.assertIn("完成 Flask 接口开发并通过测试", saved)

    def test_resume_choice_context_continues_the_workflow_without_exposing_an_id(self):
        with self.local_ai_mode():
            selection = self.client.post(
                "/api/agent/chat", json={"message": "帮我优化简历"}
            ).get_json()
            created = self.client.post(
                "/api/agent/chat",
                json={
                    "conversation_id": selection["conversation_id"],
                    "message": "我选择了这份简历，请生成优化草稿",
                    "context": {"resume_id": self.resume_id},
                },
            ).get_json()

        self.assertEqual(created["status"], "degraded")
        self.assertEqual(created["action_proposals"][0]["action_type"], "create_resume_version")

    def test_resume_choice_context_wins_over_digits_in_the_resume_title(self):
        with self.local_ai_mode():
            selection = self.client.post(
                "/api/agent/chat", json={"message": "帮我优化简历"}
            ).get_json()
            created = self.client.post(
                "/api/agent/chat",
                json={
                    "conversation_id": selection["conversation_id"],
                    "message": "已选择「测试简历2」，请生成优化草稿",
                    "context": {"resume_id": self.resume_id},
                },
            ).get_json()

        self.assertEqual(created["status"], "degraded")
        proposal_id = created["action_proposals"][0]["id"]
        draft = self.client.get(f"/api/agent/actions/{proposal_id}/draft").get_json()["draft"]
        self.assertIn("Flask 接口开发", draft["content"])
        self.assertNotIn("Playwright", draft["content"])

    def test_resume_interview_questions_are_generated_from_selected_resume_not_echoed(self):
        with self.local_ai_mode():
            response = self.client.post(
                "/api/agent/chat",
                json={
                    "message": "根据我的简历帮我出几道面试题",
                    "context": {"resume_id": self.resume_id},
                },
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["tools_used"], ["generate_resume_interview_questions"])
        self.assertIn("1.", payload["reply"])
        self.assertIn("5.", payload["reply"])
        self.assertIn("Flask", payload["reply"])
        self.assertNotIn("负责 Flask 接口开发", payload["reply"])

    def test_resume_interview_questions_prompt_for_clickable_resume_choice_when_unselected(self):
        with self.local_ai_mode():
            response = self.client.post(
                "/api/agent/chat", json={"message": "根据我的简历帮我出几道面试题"}
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "needs_input")
        self.assertEqual(payload["input_request"]["kind"], "resume_select")
        self.assertEqual(payload["input_request"]["workflow"], "interview_questions")

    def test_local_agent_diagnoses_the_selected_resume_without_a_model_key(self):
        with self.local_ai_mode():
            selection = self.client.post(
                "/api/agent/chat", json={"message": "选择一份简历进行诊断"}
            ).get_json()
            diagnosed = self.client.post(
                "/api/agent/chat",
                json={
                    "conversation_id": selection["conversation_id"],
                    "message": f"选择简历 #{self.resume_id}，进行简历诊断",
                },
            ).get_json()

        self.assertEqual(diagnosed["status"], "degraded")
        self.assertIn("diagnose_resume", diagnosed["tools_used"])
        self.assertIn("本地简历诊断", diagnosed["reply"])

    def test_draft_endpoint_rejects_non_resume_proposals(self):
        action = self.container.agent.action_service.propose(
            1, "create_action_item", {"title": "Prepare interview"}
        )
        response = self.client.get(f"/api/agent/actions/{action['id']}/draft")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "draft_not_available")


if __name__ == "__main__":
    unittest.main()

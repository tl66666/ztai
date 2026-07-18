import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from utils.agent_runtime.models import ToolResult
from utils.agent_runtime.tools import ToolDefinition, ToolRegistry, build_tool_registry


class AgentToolTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "tools.db")
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executescript(
                """
                CREATE TABLE resumes (
                    id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, content TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE job_applications (
                    id INTEGER PRIMARY KEY, user_id INTEGER, company TEXT, job_title TEXT,
                    status TEXT, city TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE job_matches (
                    id INTEGER PRIMARY KEY, user_id INTEGER, resume_id INTEGER,
                    job_title TEXT, match_score INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE interviews (
                    id INTEGER PRIMARY KEY, user_id INTEGER, job_title TEXT, score INTEGER,
                    feedback TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO resumes(id, user_id, title, content)
                VALUES (1, 1, '测试简历', 'Python 接口自动化测试项目完整正文与量化结果'),
                       (2, 2, '他人简历', '不应被用户一读取');
                """
            )
        finally:
            connection.close()
        self.registry = build_tool_registry(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_runtime_injects_user_id_instead_of_trusting_model(self):
        result = self.registry.execute("list_resumes", {"user_id": 2}, user_id=1)

        self.assertTrue(result.ok)
        self.assertEqual([item["id"] for item in result.data], [1])
        self.assertTrue(all(item["user_id"] == 1 for item in result.data))

    def test_get_resume_returns_owned_full_content(self):
        result = self.registry.execute("get_resume", {"resume_id": 1}, user_id=1)

        self.assertTrue(result.ok)
        self.assertIn("完整正文", result.data["content"])

    def test_get_resume_does_not_cross_user_boundary(self):
        result = self.registry.execute("get_resume", {"resume_id": 2}, user_id=1)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "not_found")

    def test_agent_resume_analysis_does_not_wait_on_a_second_model_call(self):
        class ConnectedClient:
            api_key = "configured"

            def analyze_resume(self, *args, **kwargs):
                raise AssertionError("Agent tools must not make a nested model request")

        with patch("utils.agent_runtime.tools.get_ai_client", return_value=ConnectedClient(), create=True):
            result = self.registry.execute("analyze_resume", {"resume_id": 1}, user_id=1)

        self.assertTrue(result.ok)
        self.assertIn("本地简历诊断", result.display_text)

    def test_agent_job_match_does_not_wait_on_a_second_model_call(self):
        class ConnectedClient:
            api_key = "configured"

            def match_job(self, *args, **kwargs):
                raise AssertionError("Agent tools must not make a nested model request")

        with patch("utils.agent_runtime.tools.get_ai_client", return_value=ConnectedClient(), create=True):
            result = self.registry.execute(
                "match_job", {"resume_id": 1, "job_title": "Python 测试工程师", "jd": "Python 接口自动化测试"}, user_id=1
            )

        self.assertTrue(result.ok)
        self.assertIn("本地岗位匹配", result.display_text)

    def test_agent_jd_analysis_does_not_wait_on_a_second_model_call(self):
        class ConnectedClient:
            api_key = "configured"

            def chat(self, *args, **kwargs):
                raise AssertionError("Agent tools must not make a nested model request")

        with patch("utils.agent_runtime.tools.get_ai_client", return_value=ConnectedClient(), create=True):
            result = self.registry.execute(
                "analyze_jd", {"jd_text": "负责 Python 接口自动化测试和质量保障"}, user_id=1
            )

        self.assertTrue(result.ok)
        self.assertIn("本地 JD 要点", result.display_text)

    def test_invalid_arguments_return_stable_error(self):
        result = self.registry.execute(
            "match_job", {"resume_id": "bad", "job_title": ""}, user_id=1
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_non_object_arguments_return_stable_error_instead_of_raising(self):
        result = self.registry.execute("get_resume", [], user_id=1)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_unexpected_executor_exception_is_contained(self):
        registry = ToolRegistry(self.db_path)

        def broken(arguments, context):
            raise RuntimeError("unexpected")

        registry.register(ToolDefinition("broken", "测试", {"type": "object"}, broken))

        result = registry.execute("broken", {}, user_id=1)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "tool_error")

    def test_tool_timeout_is_enforced(self):
        registry = ToolRegistry(self.db_path)
        completed = []

        def slow(arguments, context):
            while True:
                time.sleep(0.005)
                context.check_timeout()
                if time.monotonic() - started > 0.2:
                    break
            completed.append(True)
            return ToolResult(True, display_text="too late")

        registry.register(
            ToolDefinition(
                "slow", "测试超时", {"type": "object"}, slow, timeout_seconds=0.02
            )
        )
        started = time.monotonic()

        result = registry.execute("slow", {}, user_id=1)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "tool_timeout")
        self.assertLess(time.monotonic() - started, 0.15)
        time.sleep(0.05)
        self.assertEqual(completed, [])

    def test_registry_exposes_machine_readable_function_schemas(self):
        schemas = self.registry.schemas(["get_resume"])

        self.assertEqual(schemas[0]["type"], "function")
        self.assertEqual(schemas[0]["function"]["name"], "get_resume")
        self.assertEqual(
            schemas[0]["function"]["parameters"]["properties"]["resume_id"]["type"],
            "integer",
        )

    def test_fetch_webpage_rejects_private_network_targets(self):
        result = self.registry.execute(
            "fetch_webpage", {"url": "http://127.0.0.1:5000/private"}, user_id=1
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unsafe_url")

    def test_fetch_webpage_streams_and_caps_the_download(self):
        class StreamingResponse:
            headers = {"Content-Type": "text/html; charset=utf-8"}
            encoding = "utf-8"

            @property
            def content(self):
                raise AssertionError("full response content must not be buffered")

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size):
                for _ in range(300):
                    yield b"a" * 1024

            def close(self):
                return None

        with patch("utils.agent_runtime.tools._is_safe_public_url", return_value=True), patch(
            "utils.agent_runtime.tools.requests.get", return_value=StreamingResponse()
        ) as request_get:
            result = self.registry.execute(
                "fetch_webpage", {"url": "https://example.com/page"}, user_id=1
            )

        self.assertTrue(result.ok)
        self.assertLessEqual(len(result.data["text"]), 6000)
        self.assertTrue(request_get.call_args.kwargs["stream"])


if __name__ == "__main__":
    unittest.main()

import os
import sqlite3
import tempfile
import unittest

from utils.agent_runtime.tools import build_tool_registry


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

    def test_invalid_arguments_return_stable_error(self):
        result = self.registry.execute(
            "match_job", {"resume_id": "bad", "job_title": ""}, user_id=1
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_arguments")

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


if __name__ == "__main__":
    unittest.main()

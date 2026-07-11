import unittest
from unittest.mock import patch

import requests

from utils.ai_client import MultiModelAIClient


DASHBOARD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_dashboard",
        "description": "读取求职看板",
        "parameters": {"type": "object", "properties": {}},
    },
}


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        self.text = str(payload)

    def json(self):
        return self.payload


class AIClientToolTests(unittest.TestCase):
    def test_chat_sends_tools_and_returns_full_tool_call_message(self):
        captured = {}
        response = FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "get_dashboard", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ],
                "usage": {"total_tokens": 30},
            },
        )

        def fake_post(*args, **kwargs):
            captured.update(kwargs["json"])
            return response

        with patch("utils.ai_client.requests.post", side_effect=fake_post):
            result = MultiModelAIClient(api_key="key").chat(
                [{"role": "user", "content": "看板"}],
                tools=[DASHBOARD_SCHEMA],
                tool_choice="auto",
            )

        self.assertEqual(captured["tools"], [DASHBOARD_SCHEMA])
        self.assertEqual(captured["tool_choice"], "auto")
        self.assertTrue(result["success"])
        self.assertEqual(
            result["message"]["tool_calls"][0]["function"]["name"],
            "get_dashboard",
        )

    def test_remote_rate_limit_is_diagnostic_not_fake_local_success(self):
        with patch(
            "utils.ai_client.requests.post",
            return_value=FakeResponse(429, {"error": "limited"}),
        ):
            result = MultiModelAIClient(api_key="key").chat(
                [{"role": "user", "content": "你好"}]
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "rate_limited")
        self.assertNotIn("本地求职 Agent 分析", result.get("content", ""))

    def test_timeout_has_stable_error_code(self):
        with patch(
            "utils.ai_client.requests.post",
            side_effect=requests.Timeout("slow"),
        ):
            result = MultiModelAIClient(api_key="key").chat(
                [{"role": "user", "content": "你好"}]
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "timeout")


if __name__ == "__main__":
    unittest.main()

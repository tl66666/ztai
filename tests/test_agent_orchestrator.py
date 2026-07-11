import os
import tempfile
import time
import unittest

from utils.agent_runtime.context import ContextBuilder
from utils.agent_runtime.memory import MemoryStore, create_agent_tables
from utils.agent_runtime.models import AgentDecision, ToolResult
from utils.agent_runtime.orchestrator import AgentOrchestrator, RemoteModelPolicy
from utils.agent_runtime.local_policy import LocalPolicy


class QueuePolicy:
    ai_used = True

    def __init__(self, decisions):
        self.decisions = list(decisions)

    def decide(self, state, tool_schemas):
        return self.decisions.pop(0)


class RepeatPolicy:
    ai_used = True

    def decide(self, state, tool_schemas):
        return AgentDecision("tool_call", "get_dashboard", {})


class SlowPolicy:
    ai_used = True

    def decide(self, state, tool_schemas):
        time.sleep(0.04)
        return AgentDecision("tool_call", "get_dashboard", {})


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def schemas(self, names=None):
        return []

    def execute(self, name, arguments, user_id, timeout_seconds=None):
        self.calls.append((name, arguments, user_id))
        if name == "get_dashboard":
            return ToolResult(True, {"resumes": 2}, "你目前有 2 份简历")
        if name == "match_job":
            return ToolResult(True, {"score": 82}, "岗位匹配度 82 分")
        return ToolResult(False, display_text="未知工具", error_code="unknown_tool")


class FakeAIClient:
    api_key = "key"
    provider = type("Provider", (), {"id": "fake"})()
    model = "fake-model"

    def __init__(self, result):
        self.result = result

    def chat(self, *args, **kwargs):
        return self.result


class SequenceAIClient(FakeAIClient):
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": [dict(item) for item in messages], **kwargs})
        return self.results.pop(0)


class AgentOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "runtime.db")
        create_agent_tables(self.db_path)
        self.store = MemoryStore(self.db_path)
        self.conversation = self.store.create_conversation(1, "编排测试")
        self.registry = FakeRegistry()
        self.context_builder = ContextBuilder(self.store, self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_orchestrator(self, policy):
        return AgentOrchestrator(
            policy=policy,
            tools=self.registry,
            store=self.store,
            context_builder=self.context_builder,
            max_iterations=4,
        )

    def test_orchestrator_executes_tool_then_returns_final_answer(self):
        policy = QueuePolicy([
            AgentDecision("tool_call", "get_dashboard", {}),
            AgentDecision("final", message="你目前有 2 份简历。"),
        ])

        result = self.make_orchestrator(policy).run(1, self.conversation.id, "看我的进度")

        self.assertEqual(result.tools_used, ["get_dashboard"])
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.reply, "你目前有 2 份简历。")
        self.assertEqual(self.registry.calls[0][2], 1)

    def test_repeated_identical_tool_call_stops_with_degraded_result(self):
        result = self.make_orchestrator(RepeatPolicy()).run(
            1, self.conversation.id, "看板"
        )

        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.tools_used, ["get_dashboard"])
        self.assertIn("重复", result.reply)

    def test_total_runtime_budget_stops_before_late_tool_execution(self):
        orchestrator = AgentOrchestrator(
            policy=SlowPolicy(),
            tools=self.registry,
            store=self.store,
            context_builder=self.context_builder,
            max_iterations=4,
            max_runtime_seconds=0.01,
        )

        result = orchestrator.run(1, self.conversation.id, "看板")

        self.assertEqual(result.status, "degraded")
        self.assertIn("时间预算", result.reply)
        self.assertEqual(self.registry.calls, [])

    def test_local_policy_persists_missing_slot_and_continues_next_turn(self):
        orchestrator = self.make_orchestrator(LocalPolicy())

        first = orchestrator.run(1, self.conversation.id, "帮我匹配岗位")
        second = orchestrator.run(1, self.conversation.id, "Python 测试工程师")

        self.assertEqual(first.status, "needs_input")
        self.assertIn("目标岗位", first.reply)
        self.assertEqual(second.status, "degraded")
        self.assertIn("82", second.reply)
        self.assertEqual(self.registry.calls[-1][0], "match_job")

    def test_explicit_facts_and_run_audit_are_persisted(self):
        policy = QueuePolicy([AgentDecision("final", message="已记住。")])

        self.make_orchestrator(policy).run(
            1, self.conversation.id, "我想去杭州，目标岗位是测试工程师"
        )

        memories = self.store.list_memories(1, kind="semantic", statuses=("confirmed",))
        self.assertEqual({item["memory_key"] for item in memories}, {"target_city", "target_role"})
        self.assertEqual(self.store.run_count(self.conversation.id, 1), 1)

    def test_completed_run_becomes_retrievable_episodic_memory(self):
        policy = QueuePolicy([
            AgentDecision("tool_call", "get_dashboard", {}),
            AgentDecision("final", message="你目前有 2 份简历。"),
        ])
        self.make_orchestrator(policy).run(1, self.conversation.id, "总结我的求职进度")

        episodes = self.store.list_memories(
            1, kind="episodic", statuses=("confirmed",)
        )
        fresh_conversation = self.store.create_conversation(1, "新会话")
        context = self.context_builder.build(1, fresh_conversation.id, "求职进度")

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["value"]["tools"], ["get_dashboard"])
        self.assertIn("2 份简历", "\n".join(context.episodes))
        self.assertIn("2 份简历", context.as_prompt())

    def test_local_policy_reuses_remembered_role_for_resume_match(self):
        orchestrator = self.make_orchestrator(LocalPolicy())
        orchestrator.run(
            1,
            self.conversation.id,
            "我想去杭州，目标岗位是 Python 测试工程师",
        )

        result = orchestrator.run(
            1, self.conversation.id, "按刚才的岗位看看我的简历"
        )

        self.assertEqual(self.registry.calls[-1][0], "match_job")
        self.assertEqual(self.registry.calls[-1][1]["job_title"], "Python 测试工程师")
        self.assertIn("82", result.reply)

    def test_remote_policy_uses_native_tool_calls(self):
        client = FakeAIClient({
            "success": True,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_dashboard", "arguments": "{}"},
                }],
            },
        })
        policy = RemoteModelPolicy(client)
        state = type("State", (), {
            "model_messages": [], "context_prompt": "", "observations": [],
            "user_message": "看板",
        })()

        decision = policy.decide(state, [])

        self.assertEqual(decision.type, "tool_call")
        self.assertEqual(decision.tool, "get_dashboard")
        self.assertEqual(decision.call_id, "call_1")

    def test_remote_tool_result_uses_assistant_and_tool_roles_on_next_decision(self):
        client = SequenceAIClient([
            {
                "success": True,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_dashboard", "arguments": "{}"},
                    }],
                },
            },
            {
                "success": True,
                "message": {"role": "assistant", "content": "你目前有 2 份简历。"},
            },
        ])

        result = self.make_orchestrator(RemoteModelPolicy(client)).run(
            1, self.conversation.id, "看我的进度"
        )

        second_messages = client.calls[1]["messages"]
        self.assertEqual(result.status, "completed")
        self.assertTrue(any(item.get("tool_calls") for item in second_messages if item["role"] == "assistant"))
        tool_message = next(item for item in second_messages if item["role"] == "tool")
        self.assertEqual(tool_message["tool_call_id"], "call_1")
        self.assertIn('"ok": true', tool_message["content"])

    def test_remote_policy_receives_persisted_active_task_slots(self):
        client = SequenceAIClient([
            {"success": True, "message": {"role": "assistant", "content": "继续处理。"}}
        ])
        state = type("State", (), {
            "model_messages": [],
            "context_prompt": "上下文",
            "observations": [],
            "user_message": "这是 JD 原文",
            "active_task": {
                "task_type": "match_job",
                "slots": {"job_title": "Python 测试工程师"},
            },
            "deadline": 9999999999,
        })()

        RemoteModelPolicy(client).decide(state, [])

        prompt = client.calls[0]["messages"][1]["content"]
        self.assertIn("match_job", prompt)
        self.assertIn("Python 测试工程师", prompt)

    def test_remote_policy_only_accepts_strict_json_fallback(self):
        client = FakeAIClient({
            "success": True,
            "message": {
                "role": "assistant",
                "content": '{"type":"needs_input","message":"请提供 JD"}',
            },
        })
        decision = RemoteModelPolicy(client).decide(
            type("State", (), {
                "model_messages": [], "context_prompt": "", "observations": [],
                "user_message": "分析 JD",
            })(),
            [],
        )

        self.assertEqual(decision.type, "needs_input")
        self.assertEqual(decision.message, "请提供 JD")


if __name__ == "__main__":
    unittest.main()

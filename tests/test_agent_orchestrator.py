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
            return ToolResult(
                True,
                {
                    "resumes": 2,
                    "matches": 1,
                    "interviews": 0,
                    "applications": 1,
                    "readiness": {"score": 46, "label": "起步期"},
                },
                "简历=2；匹配=1；面试=0；投递=1；求职准备度=46（起步期）",
            )
        if name == "get_career_profile":
            return ToolResult(
                True,
                {"target_role": "Python 测试工程师", "cities": ["杭州"]},
                '{"target_role": "Python 测试工程师", "cities": ["杭州"]}',
            )
        if name == "list_action_items":
            return ToolResult(
                True,
                [{"id": 3, "title": "补充接口自动化项目", "status": "todo"}],
                "#3 补充接口自动化项目 / todo",
            )
        if name == "get_training_insights":
            return ToolResult(
                True,
                {
                    "interviews": {"completed_count": 0},
                    "practice": {"completed_count": 2},
                    "audio": {"completed_count": 0},
                },
                "最近完成训练：面试 0 次，题库 2 次，语音 0 次",
            )
        if name == "list_applications":
            return ToolResult(
                True,
                [{"company": "星河科技", "job_title": "测试工程师", "status": "已投递"}],
                "星河科技 / 测试工程师 / 已投递",
            )
        if name == "analyze_resume":
            return ToolResult(
                True,
                {"analysis": "建议补充量化结果、技术关键词和项目职责。"},
                "建议补充量化结果、技术关键词和项目职责。",
            )
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

    def test_local_policy_chains_business_tools_and_synthesizes_next_steps(self):
        result = self.make_orchestrator(LocalPolicy()).run(
            1,
            self.conversation.id,
            "帮我分析现在的求职情况，我下一步该做什么？",
        )

        self.assertEqual(
            result.tools_used,
            [
                "get_dashboard",
                "get_career_profile",
                "list_action_items",
                "get_training_insights",
            ],
        )
        self.assertIn("本地求职 Agent", result.reply)
        self.assertIn("Python 测试工程师", result.reply)
        self.assertIn("杭州", result.reply)
        self.assertIn("优先级 1", result.reply)
        self.assertIn("面试训练", result.reply)
        self.assertNotIn("当前未配置大模型 API", result.reply)

    def test_local_policy_explains_capabilities_without_api_key(self):
        result = self.make_orchestrator(LocalPolicy()).run(
            1, self.conversation.id, "你能做什么？"
        )

        self.assertEqual(result.tools_used, [])
        self.assertIn("本地求职 Agent", result.reply)
        self.assertIn("求职诊断", result.reply)
        self.assertIn("简历", result.reply)
        self.assertIn("投递", result.reply)
        self.assertIn("写入操作", result.reply)

    def test_local_policy_routes_common_career_paraphrases(self):
        cases = (
            ("帮我看看现在有哪些机会", ["list_applications"], "星河科技"),
            ("面试准备得怎么样", ["get_dashboard", "get_training_insights"], "面试训练"),
            ("帮我优化一下简历", ["analyze_resume"], "量化结果"),
        )

        for index, (message, expected_tools, expected_text) in enumerate(cases):
            with self.subTest(message=message):
                conversation = self.store.create_conversation(1, f"paraphrase-{index}")
                result = self.make_orchestrator(LocalPolicy()).run(
                    1, conversation.id, message
                )
                self.assertEqual(result.tools_used, expected_tools)
                self.assertIn(expected_text, result.reply)

    def test_local_policy_unknown_request_returns_actionable_examples(self):
        result = self.make_orchestrator(LocalPolicy()).run(
            1, self.conversation.id, "我最近有点迷茫，不知道从哪里开始"
        )

        self.assertEqual(result.tools_used, [])
        self.assertIn("可以直接这样问", result.reply)
        self.assertIn("下一步", result.reply)
        self.assertNotEqual(
            result.reply,
            "当前未配置大模型 API，正在使用本地模板和规则模式，不会进行模型生成。",
        )

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

    def test_remote_parallel_tool_calls_all_receive_tool_responses(self):
        client = SequenceAIClient([
            {
                "success": True,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "get_dashboard", "arguments": "{}"}},
                        {"id": "call_2", "type": "function", "function": {"name": "get_dashboard", "arguments": '{"view":"detail"}'}},
                    ],
                },
            },
            {"success": True, "message": {"role": "assistant", "content": "汇总完成。"}},
        ])

        result = self.make_orchestrator(RemoteModelPolicy(client)).run(
            1, self.conversation.id, "读取两组看板数据"
        )

        final_messages = client.calls[1]["messages"]
        tool_messages = [item for item in final_messages if item["role"] == "tool"]
        self.assertEqual(result.status, "completed")
        self.assertEqual({item["tool_call_id"] for item in tool_messages}, {"call_1", "call_2"})

    def test_remote_needs_input_without_metadata_still_persists_task(self):
        client = SequenceAIClient([
            {
                "success": True,
                "message": {
                    "role": "assistant",
                    "content": '{"type":"needs_input","message":"请提供 JD"}',
                },
            }
        ])

        result = self.make_orchestrator(RemoteModelPolicy(client)).run(
            1, self.conversation.id, "帮我分析岗位"
        )

        active_task = self.store.get_active_task(self.conversation.id, 1)
        self.assertEqual(result.status, "needs_input")
        self.assertIsNotNone(active_task)
        self.assertEqual(active_task["task_type"], "clarification")

    def test_clarification_task_completes_when_next_turn_answers_directly(self):
        needs_client = SequenceAIClient([{
            "success": True,
            "message": {
                "role": "assistant",
                "content": '{"type":"needs_input","message":"请提供 JD"}',
            },
        }])
        self.make_orchestrator(RemoteModelPolicy(needs_client)).run(
            1, self.conversation.id, "帮我分析岗位"
        )
        final_client = SequenceAIClient([{
            "success": True,
            "message": {"role": "assistant", "content": "这份 JD 的重点是接口自动化。"},
        }])

        result = self.make_orchestrator(RemoteModelPolicy(final_client)).run(
            1, self.conversation.id, "JD 要求 Python 和接口自动化"
        )

        self.assertEqual(result.status, "completed")
        self.assertIsNone(self.store.get_active_task(self.conversation.id, 1))

    def test_remote_non_object_json_fallback_becomes_safe_final(self):
        client = FakeAIClient({
            "success": True,
            "message": {"role": "assistant", "content": "[]"},
        })
        state = type("State", (), {
            "model_messages": [], "context_prompt": "", "observations": [],
            "user_message": "分析", "active_task": None,
        })()

        decision = RemoteModelPolicy(client).decide(state, [])

        self.assertEqual(decision.type, "final")
        self.assertIn("无法识别", decision.message)

    def test_four_parallel_tool_calls_still_get_a_final_model_turn(self):
        tool_calls = [
            {
                "id": f"call_{index}",
                "type": "function",
                "function": {
                    "name": "get_dashboard",
                    "arguments": f'{{"view":{index}}}',
                },
            }
            for index in range(4)
        ]
        client = SequenceAIClient([
            {
                "success": True,
                "message": {"role": "assistant", "content": None, "tool_calls": tool_calls},
            },
            {
                "success": True,
                "message": {"role": "assistant", "content": "四组数据已汇总。"},
            },
        ])

        result = self.make_orchestrator(RemoteModelPolicy(client)).run(
            1, self.conversation.id, "汇总四组数据"
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.reply, "四组数据已汇总。")
        self.assertEqual(len(result.tools_used), 4)

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

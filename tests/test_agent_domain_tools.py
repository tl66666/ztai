import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from utils.agent_runtime.context import ContextBuilder
from utils.agent_runtime.actions import ALLOWED_ACTION_TYPES
from utils.agent_runtime.local_policy import LocalPolicy
from utils.agent_runtime.memory import MemoryStore, create_agent_tables
from utils.agent_runtime.models import AgentDecision
from utils.agent_runtime.orchestrator import AgentOrchestrator
from utils.agent_runtime.orchestrator import RemoteModelPolicy
from utils.agent_runtime.tools import build_tool_registry
from utils.domain.career import CareerService
from utils.domain.database import connect, migrate_database


class QueuePolicy:
    ai_used = True
    provider = "test"
    model = "queue"

    def __init__(self, decisions):
        self.decisions = list(decisions)

    def decide(self, state, tool_schemas):
        return self.decisions.pop(0)


class SequenceClient:
    api_key = "test-key"
    provider = type("Provider", (), {"id": "test"})()
    model = "test-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": [dict(item) for item in messages], **kwargs})
        return self.responses.pop(0)


class AgentDomainToolTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "agent-domain.db")
        migrate_database(self.db_path)
        create_agent_tables(self.db_path)
        with connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    job_title TEXT, score INTEGER, feedback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS practice_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    category TEXT, correct_count INTEGER, total_count INTEGER,
                    score INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audio_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    duration REAL, analysis_result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        self.career = CareerService(self.db_path)
        self.registry = build_tool_registry(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_domain_reads_match_career_service_and_filter_deleted_and_foreign(self):
        self.career.upsert_profile(1, {"target_role": "测试工程师"})
        kept = self.career.create_opportunity(
            1, {"company": "星河科技", "job_title": "测试工程师"}
        )
        deleted = self.career.create_opportunity(
            1, {"company": "已删除公司", "job_title": "秘密岗位"}
        )
        self.career.delete_opportunity(1, deleted["id"])
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO job_applications(user_id, company, job_title) VALUES (2, '他人公司', '私密岗位')"
            )

        listing = self.registry.execute("list_applications", {}, user_id=1)
        profile = self.registry.execute("get_career_profile", {}, user_id=1)
        detail = self.registry.execute(
            "get_opportunity", {"opportunity_id": kept["id"]}, user_id=1
        )
        dashboard = self.registry.execute("get_dashboard", {}, user_id=1)
        report = self.registry.execute("generate_career_report", {}, user_id=1)

        self.assertEqual(listing.data, self.career.list_opportunities(1))
        self.assertEqual(profile.data, self.career.get_profile(1))
        self.assertEqual(detail.data, self.career.get_opportunity(1, kept["id"]))
        self.assertEqual(dashboard.data["readiness"], self.career.calculate_readiness(1))
        self.assertEqual(report.data["opportunities"], self.career.list_opportunities(1))
        serialized = json.dumps([listing.data, dashboard.data, report.data], ensure_ascii=False)
        self.assertNotIn("已删除公司", serialized)
        self.assertNotIn("他人公司", serialized)

        missing = self.registry.execute(
            "get_opportunity", {"opportunity_id": deleted["id"]}, user_id=1
        )
        self.assertFalse(missing.ok)
        self.assertEqual(missing.error_code, "not_found")

    def test_proposal_tool_creates_only_pending_redacted_proposal_for_fixed_user(self):
        secret = "private@example.com"
        result = self.registry.execute(
            "propose_career_action",
            {
                "user_id": 2,
                "action_type": "create_opportunity",
                "arguments": {
                    "company": "星河科技",
                    "job_title": "测试工程师",
                    "contact_info": secret,
                },
                "rationale": "记录用户明确提供的投递信息",
            },
            user_id=1,
        )

        self.assertTrue(result.ok, result.display_text)
        self.assertEqual(result.data["status"], "pending")
        self.assertNotIn("arguments", result.data)
        self.assertNotIn(secret, json.dumps(result.data, ensure_ascii=False))
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT user_id FROM agent_action_proposals").fetchone()[0], 1
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM job_applications").fetchone()[0], 0)

    def test_registry_rejects_nonlocal_runtime_identity(self):
        result = self.registry.execute("get_career_profile", {}, user_id=2)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "forbidden")

    def test_status_filtered_action_and_proposal_reads_return_public_data(self):
        pending = self.career.create_action_item(1, {"title": "准备面试"})
        completed = self.career.create_action_item(1, {"title": "完成复盘"})
        self.career.complete_action_item(1, completed["id"], "done")
        self.registry.execute(
            "propose_career_action",
            {
                "action_type": "create_action_item",
                "arguments": {"title": "跟进招聘方", "description": "private body"},
                "rationale": "下一步",
            },
            user_id=1,
        )

        actions = self.registry.execute(
            "list_action_items", {"status": "pending"}, user_id=1
        )
        proposals = self.registry.execute(
            "list_agent_actions", {"status": "pending"}, user_id=1
        )

        self.assertEqual([item["id"] for item in actions.data], [pending["id"]])
        self.assertEqual(len(proposals.data), 1)
        self.assertNotIn("arguments", proposals.data[0])
        self.assertNotIn("private body", json.dumps(proposals.data, ensure_ascii=False))

    def test_training_insights_return_quality_summary_without_private_content(self):
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO interviews(user_id, job_title, score, feedback) VALUES (1, '测试工程师', 82, 'private feedback')"
            )
            conn.execute(
                "INSERT INTO practice_records(user_id, category, correct_count, total_count, score) VALUES (1, 'Python', 8, 10, 80)"
            )
            conn.execute(
                "INSERT INTO audio_records(user_id, duration, analysis_result) VALUES (1, 45, ?)",
                (json.dumps({"overall_score": 76, "transcript": "private audio transcript"}),),
            )
            conn.execute(
                "INSERT INTO interviews(user_id, job_title, score, feedback) VALUES (2, '私密岗位', 99, 'foreign feedback')"
            )

        result = self.registry.execute("get_training_insights", {}, user_id=1)
        serialized = json.dumps(result.data, ensure_ascii=False)

        self.assertTrue(result.ok)
        self.assertEqual(result.data["interviews"]["average_score"], 82)
        self.assertEqual(result.data["practice"]["average_score"], 80)
        self.assertEqual(result.data["audio"]["average_quality_score"], 76)
        self.assertNotIn("private feedback", serialized)
        self.assertNotIn("private audio transcript", serialized)
        self.assertNotIn("foreign feedback", serialized)

    def test_registry_exposes_strict_new_schemas_without_confirmation_tools(self):
        schemas = {
            item["function"]["name"]: item["function"]["parameters"]
            for item in self.registry.schemas()
        }
        expected = {
            "get_career_profile",
            "get_opportunity",
            "get_training_insights",
            "list_action_items",
            "list_agent_actions",
            "propose_career_action",
        }

        self.assertTrue(expected.issubset(schemas))
        self.assertNotIn("confirm_agent_action", schemas)
        self.assertNotIn("cancel_agent_action", schemas)
        self.assertTrue(all(schema["additionalProperties"] is False for schema in schemas.values()))
        proposal = schemas["propose_career_action"]
        self.assertEqual(len(proposal["properties"]["action_type"]["enum"]), 9)
        self.assertEqual(proposal["properties"]["arguments"]["type"], "object")
        self.assertEqual(proposal["properties"]["rationale"]["maxLength"], 1000)

    def test_proposal_schema_has_nine_exact_action_specific_branches(self):
        schema = next(
            item["function"]["parameters"]
            for item in self.registry.schemas()
            if item["function"]["name"] == "propose_career_action"
        )
        branches = {
            branch["properties"]["action_type"]["const"]: branch
            for branch in schema["oneOf"]
        }

        self.assertEqual(set(branches), set(ALLOWED_ACTION_TYPES))
        self.assertFalse(schema["additionalProperties"])
        opportunity = branches["create_opportunity"]["properties"]["arguments"]
        self.assertEqual(set(opportunity["required"]), {"company", "job_title"})
        self.assertFalse(opportunity["additionalProperties"])
        metadata = branches["create_resume_version"]["properties"]["arguments"]["properties"]["metadata"]
        changes = branches["update_opportunity"]["properties"]["arguments"]["properties"]["changes"]
        report_content = branches["save_career_report"]["properties"]["arguments"]["properties"]["content"]
        self.assertFalse(metadata["additionalProperties"])
        self.assertFalse(changes["additionalProperties"])
        self.assertIsInstance(report_content["additionalProperties"], dict)

    def test_nested_invalid_arguments_are_rejected_before_proposal_executor(self):
        invalid = (
            {
                "action_type": "create_opportunity",
                "arguments": {"company": "Acme", "job_title": "Engineer", "unknown": True},
            },
            {
                "action_type": "create_resume_version",
                "arguments": {
                    "resume_id": 1,
                    "content": "body",
                    "metadata": {"unknown": True},
                },
            },
            {
                "action_type": "save_career_report",
                "arguments": {
                    "report_type": "weekly",
                    "content": {"summary": object()},
                },
            },
            {
                "action_type": "save_career_report",
                "arguments": {
                    "report_type": "weekly",
                    "content": {"score": 10 ** 1000},
                },
            },
        )
        with patch(
            "utils.agent_runtime.tools.ActionProposalService.propose"
        ) as propose:
            results = [
                self.registry.execute("propose_career_action", item, user_id=1)
                for item in invalid
            ]

        self.assertTrue(all(not item.ok for item in results))
        self.assertEqual({item.error_code for item in results}, {"invalid_arguments"})
        propose.assert_not_called()
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM agent_action_proposals").fetchone()[0], 0)

    def test_model_tool_rejects_numeric_strings_before_proposal_executor(self):
        invalid_values = ("0", "000", "1000000001")
        with patch(
            "utils.agent_runtime.tools.ActionProposalService.propose"
        ) as propose:
            results = [
                self.registry.execute(
                    "propose_career_action",
                    {
                        "action_type": "create_opportunity",
                        "arguments": {
                            "company": "Acme",
                            "job_title": "Engineer",
                            "salary_min": value,
                        },
                    },
                    user_id=1,
                )
                for value in invalid_values
            ]

        self.assertTrue(all(not item.ok for item in results))
        self.assertEqual({item.error_code for item in results}, {"invalid_arguments"})
        propose.assert_not_called()
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM agent_action_proposals").fetchone()[0], 0)

    def test_model_tool_schema_uses_bounded_json_integers_and_accepts_endpoints(self):
        schema = next(
            item["function"]["parameters"]
            for item in self.registry.schemas()
            if item["function"]["name"] == "propose_career_action"
        )
        create_branch = next(
            item for item in schema["oneOf"]
            if item["properties"]["action_type"]["const"] == "create_opportunity"
        )
        properties = create_branch["properties"]["arguments"]["properties"]

        self.assertEqual(properties["salary_min"]["type"], "integer")
        self.assertEqual(properties["resume_id"]["type"], "integer")
        self.assertEqual(properties["resume_id"]["minimum"], 1)
        self.assertEqual(properties["salary_min"]["minimum"], 0)
        self.assertEqual(properties["salary_max"]["maximum"], 1_000_000_000)
        with connect(self.db_path) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes(user_id, title, content) VALUES (1, 'Owned', 'body')"
            ).lastrowid
        result = self.registry.execute(
            "propose_career_action",
            {
                "action_type": "create_opportunity",
                "arguments": {
                    "company": "Acme",
                    "job_title": "Engineer",
                    "salary_min": 0,
                    "salary_max": 1_000_000_000,
                    "priority": -1000,
                    "resume_id": resume_id,
                },
            },
            user_id=1,
        )
        self.assertTrue(result.ok, result.display_text)
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM agent_action_proposals").fetchone()[0], 1)

    def test_remote_policy_receives_constrained_nested_proposal_schema(self):
        client = SequenceClient([
            {"success": True, "message": {"role": "assistant", "content": "完成。"}}
        ])
        state = type(
            "State",
            (),
            {
                "pending_decisions": [],
                "model_messages": [],
                "active_task": None,
                "context_prompt": "",
                "observations": [],
                "user_message": "创建投递",
                "deadline": 9999999999,
            },
        )()

        RemoteModelPolicy(client).decide(state, self.registry.schemas())

        schema = next(
            item["function"]["parameters"]
            for item in client.calls[0]["tools"]
            if item["function"]["name"] == "propose_career_action"
        )
        create_branch = next(
            item for item in schema["oneOf"]
            if item["properties"]["action_type"].get("const") == "create_opportunity"
        )
        self.assertFalse(
            create_branch["properties"]["arguments"]["additionalProperties"]
        )

    def test_shared_proposal_text_is_neutral_while_local_reply_names_rule_mode(self):
        arguments = {
            "action_type": "create_action_item",
            "arguments": {"title": "准备面试"},
            "rationale": "下一步",
        }
        shared = self.registry.execute("propose_career_action", arguments, user_id=1)
        state = type(
            "State",
            (),
            {
                "observations": [{"display_text": shared.display_text}],
                "active_task": None,
                "user_message": "",
                "context_prompt": "",
            },
        )()
        local = LocalPolicy().decide(state, self.registry.schemas())

        self.assertNotIn("本地规则模式", shared.display_text)
        self.assertIn("本地规则模式", local.message)

    def test_orchestrator_attaches_and_persists_public_proposals_separately(self):
        store = MemoryStore(self.db_path)
        conversation = store.create_conversation(1, "proposal")
        orchestrator = AgentOrchestrator(
            policy=QueuePolicy(
                [
                    AgentDecision(
                        "tool_call",
                        "propose_career_action",
                        {
                            "action_type": "create_opportunity",
                            "arguments": {
                                "company": "星河科技",
                                "job_title": "测试工程师",
                                "contact_info": "secret@example.com",
                            },
                            "rationale": "记录投递",
                        },
                    ),
                    AgentDecision("final", message="请在操作卡片中确认。"),
                ]
            ),
            tools=self.registry,
            store=store,
            context_builder=ContextBuilder(store, self.db_path),
        )

        result = orchestrator.run(1, conversation.id, "帮我记录投递")
        saved = store.list_messages(conversation.id, 1)[-1]

        self.assertEqual(len(result.action_proposals), 1)
        self.assertEqual(saved.metadata["action_proposals"], result.action_proposals)
        self.assertNotIn("action_proposals", result.events)
        self.assertNotIn("secret@example.com", json.dumps(saved.metadata, ensure_ascii=False))

    def test_local_policy_distinguishes_ambiguous_read_and_collects_explicit_create(self):
        store = MemoryStore(self.db_path)
        conversation = store.create_conversation(1, "local")
        orchestrator = AgentOrchestrator(
            policy=LocalPolicy(),
            tools=self.registry,
            store=store,
            context_builder=ContextBuilder(store, self.db_path),
        )

        read = orchestrator.run(1, conversation.id, "看看我的投递")
        first = orchestrator.run(1, conversation.id, "帮我记录一条投递")
        second = orchestrator.run(1, conversation.id, "公司是星河科技")
        third = orchestrator.run(1, conversation.id, "岗位是测试工程师")

        self.assertEqual(read.tools_used, ["list_applications"])
        self.assertEqual(first.status, "needs_input")
        self.assertEqual(second.status, "needs_input")
        self.assertEqual(third.tools_used, ["propose_career_action"])
        self.assertEqual(third.action_proposals[0]["action_type"], "create_opportunity")
        self.assertIn("本地规则模式", third.reply)
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM job_applications").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM agent_action_proposals").fetchone()[0], 1)

    def test_local_policy_maps_all_supported_explicit_create_intents_to_proposals(self):
        policy = LocalPolicy()
        cases = (
            ("帮我把职业目标设为测试工程师", "set_career_goal"),
            ("创建投递，公司是星河科技，岗位是测试工程师", "create_opportunity"),
            ("创建行动项：准备模拟面试", "create_action_item"),
            ("把投递 7 的阶段更新为一面", "update_opportunity"),
            ("创建简历版本，简历 3，正文：新的简历正文", "create_resume_version"),
        )
        for message, action_type in cases:
            with self.subTest(message=message):
                state = type(
                    "State",
                    (),
                    {
                        "observations": [],
                        "active_task": None,
                        "user_message": message,
                        "context_prompt": "",
                    },
                )()
                decision = policy.decide(state, [])
                self.assertEqual(decision.type, "tool_call")
                self.assertEqual(decision.tool, "propose_career_action")
                self.assertEqual(decision.arguments["action_type"], action_type)

    def test_arbitrary_follow_up_never_becomes_confirmation_or_proposal(self):
        policy = LocalPolicy()
        state = type(
            "State",
            (),
            {
                "observations": [],
                "active_task": {
                    "task_type": "career_action",
                    "slots": {
                        "action_type": "create_opportunity",
                        "arguments": {"company": "星河科技"},
                    },
                },
                "user_message": "确认，就这样",
                "context_prompt": "",
            },
        )()

        decision = policy.decide(state, [])

        self.assertEqual(decision.type, "needs_input")
        self.assertEqual(decision.arguments["slots"]["arguments"], {"company": "星河科技"})

    def test_remote_proposal_call_keeps_structured_card_for_final_synthesis(self):
        client = SequenceClient(
            [
                {
                    "success": True,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "proposal-call",
                                "type": "function",
                                "function": {
                                    "name": "propose_career_action",
                                    "arguments": json.dumps(
                                        {
                                            "action_type": "create_action_item",
                                            "arguments": {"title": "准备面试"},
                                            "rationale": "下一步",
                                        },
                                        ensure_ascii=False,
                                    ),
                                },
                            }
                        ],
                    },
                },
                {
                    "success": True,
                    "message": {"role": "assistant", "content": "已生成待确认操作。"},
                },
            ]
        )
        store = MemoryStore(self.db_path)
        conversation = store.create_conversation(1, "remote proposal")
        orchestrator = AgentOrchestrator(
            policy=RemoteModelPolicy(client),
            tools=self.registry,
            store=store,
            context_builder=ContextBuilder(store, self.db_path),
        )

        result = orchestrator.run(1, conversation.id, "帮我创建面试准备行动项")

        self.assertEqual(result.reply, "已生成待确认操作。")
        self.assertNotIn("本地规则模式", result.reply)
        self.assertEqual(len(result.action_proposals), 1)
        tool_message = next(
            item for item in client.calls[1]["messages"] if item["role"] == "tool"
        )
        self.assertNotIn("arguments", tool_message["content"])
        self.assertNotIn("本地规则模式", tool_message["content"])


if __name__ == "__main__":
    unittest.main()

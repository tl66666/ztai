import os
import tempfile
import unittest

from utils.agent_runtime.context import ContextBuilder, extract_explicit_facts
from utils.agent_runtime.memory import MemoryStore, create_agent_tables


class AgentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "agent.db")
        create_agent_tables(self.db_path)
        self.store = MemoryStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_messages_are_isolated_by_user_and_conversation(self):
        first = self.store.create_conversation(1, "第一段对话")
        second = self.store.create_conversation(2, "第二段对话")

        self.store.add_message(first.id, 1, "user", "我的目标是测试岗")
        self.store.add_message(second.id, 2, "user", "我的目标是运营岗")

        self.assertEqual(
            [message.content for message in self.store.list_messages(first.id, 1)],
            ["我的目标是测试岗"],
        )
        self.assertEqual(self.store.list_messages(first.id, 2), [])

    def test_store_recovers_messages_after_recreation(self):
        conversation = self.store.create_conversation(1, "恢复测试")
        self.store.add_message(conversation.id, 1, "user", "记住杭州")

        restored = MemoryStore(self.db_path).list_messages(conversation.id, 1)

        self.assertEqual(restored[0].content, "记住杭州")

    def test_clear_only_removes_the_owned_conversation_messages(self):
        first = self.store.create_conversation(1, "第一段")
        second = self.store.create_conversation(1, "第二段")
        self.store.add_message(first.id, 1, "user", "清空我")
        self.store.add_message(second.id, 1, "user", "保留我")

        self.assertTrue(self.store.clear_conversation(first.id, 1))

        self.assertEqual(self.store.list_messages(first.id, 1), [])
        self.assertEqual(self.store.list_messages(second.id, 1)[0].content, "保留我")

    def test_clear_cancels_the_conversation_pending_task(self):
        conversation = self.store.create_conversation(1, "待完成")
        self.store.create_task(conversation.id, 1, "match_job", {})

        self.store.clear_conversation(conversation.id, 1)

        self.assertIsNone(self.store.get_active_task(conversation.id, 1))

    def test_new_confirmed_memory_supersedes_the_previous_value(self):
        self.store.upsert_memory(
            user_id=1,
            kind="semantic",
            category="preference",
            memory_key="target_city",
            value="上海",
            confidence=0.9,
            status="confirmed",
        )
        self.store.upsert_memory(
            user_id=1,
            kind="semantic",
            category="preference",
            memory_key="target_city",
            value="杭州",
            confidence=0.95,
            status="confirmed",
        )

        active = self.store.list_memories(1, kind="semantic", statuses=("confirmed",))
        all_memories = self.store.list_memories(
            1, kind="semantic", statuses=("confirmed", "superseded")
        )

        self.assertEqual([memory["value"] for memory in active], ["杭州"])
        self.assertEqual(
            {memory["status"] for memory in all_memories},
            {"confirmed", "superseded"},
        )

    def test_explicit_profile_facts_are_extracted_without_guessing(self):
        facts = extract_explicit_facts("我想去杭州，目标岗位是 Python 测试工程师，期望薪资 12k-15k")

        self.assertEqual(facts["target_city"], "杭州")
        self.assertEqual(facts["target_role"], "Python 测试工程师")
        self.assertEqual(facts["salary_expectation"], "12k-15k")

    def test_context_uses_recent_messages_and_active_confirmed_memories(self):
        conversation = self.store.create_conversation(1, "上下文")
        for index in range(15):
            self.store.add_message(conversation.id, 1, "user", f"消息{index}")
        self.store.upsert_memory(
            1, "semantic", "preference", "target_city", "杭州", 0.95, "confirmed"
        )
        self.store.upsert_memory(
            1, "semantic", "preference", "old_city", "上海", 0.5, "superseded"
        )

        context = ContextBuilder(self.store, self.db_path).build(
            1, conversation.id, "继续准备杭州岗位"
        )

        self.assertEqual(len(context.recent_messages), 12)
        self.assertEqual(context.recent_messages[0]["content"], "消息3")
        profile_text = "\n".join(context.profile_facts)
        self.assertIn("杭州", profile_text)
        self.assertNotIn("上海", profile_text)

    def test_long_conversation_triggers_and_saves_rolling_summary(self):
        conversation = self.store.create_conversation(1, "摘要")
        for index in range(18):
            self.store.add_message(conversation.id, 1, "user", f"第{index}条消息")
        builder = ContextBuilder(self.store, self.db_path)

        self.assertTrue(builder.needs_summary(conversation.id, 1))
        summary = builder.summarize(conversation.id, 1)

        restored = self.store.get_conversation(conversation.id, 1)
        self.assertIn("当前目标", summary)
        self.assertEqual(restored.summary, summary)
        self.assertFalse(builder.needs_summary(conversation.id, 1))

        for index in range(16):
            self.store.add_message(conversation.id, 1, "user", f"摘要后消息{index}")
        self.assertFalse(builder.needs_summary(conversation.id, 1))
        self.store.add_message(conversation.id, 1, "user", "摘要后第17条")
        self.assertTrue(builder.needs_summary(conversation.id, 1))


if __name__ == "__main__":
    unittest.main()

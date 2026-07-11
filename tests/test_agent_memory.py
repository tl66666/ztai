import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()

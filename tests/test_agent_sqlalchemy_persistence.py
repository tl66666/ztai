from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core.database import Database, sqlite_database_url
from utils.agent_runtime.actions import ActionProposalService
from utils.agent_runtime.memory import MemoryStore
from utils.agent_runtime.service import AgentService


class AgentSqlAlchemyPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.db_path = Path(self._temporary_directory.name) / "agent.db"
        self.database = Database(sqlite_database_url(self.db_path))
        self.addCleanup(self.database.dispose)
        self.database.upgrade()
        self.database.ensure_local_user(1)

    def test_agent_service_accepts_application_session_factory(self) -> None:
        with patch(
            "utils.agent_runtime.service.create_agent_tables",
            side_effect=AssertionError("Alembic owns production schema"),
        ):
            service = AgentService(
                str(self.db_path),
                session_factory=self.database.session_factory,
            )
        conversation = service.create_conversation(1, "SQLAlchemy")
        self.assertEqual(conversation["title"], "SQLAlchemy")
        self.assertEqual(service.list_conversations(1)[0]["id"], conversation["id"])

    def test_memory_and_action_adapters_share_injected_transactions(self) -> None:
        store = MemoryStore(
            str(self.db_path),
            session_factory=self.database.session_factory,
        )
        conversation = store.create_conversation(1, "shared")
        store.add_message(conversation.id, 1, "user", "记住杭州")
        self.assertEqual(store.message_count(conversation.id, 1), 1)

        actions = ActionProposalService(
            self.db_path,
            local_user_id=1,
            session_factory=self.database.session_factory,
        )
        proposal = actions.propose(
            1,
            "set_career_goal",
            {"target_role": "后端工程师"},
        )
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(actions.list_pending(1)[0]["id"], proposal["id"])


if __name__ == "__main__":
    unittest.main()

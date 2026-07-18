from __future__ import annotations

from dataclasses import asdict

from utils.agent_runtime.context import ContextBuilder
from utils.agent_runtime.local_policy import LocalPolicy
from utils.agent_runtime.memory import MemoryStore, create_agent_tables
from utils.agent_runtime.orchestrator import AgentOrchestrator, RemoteModelPolicy
from utils.agent_runtime.tools import build_tool_registry
from utils.ai_client import get_ai_client


class AgentService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        create_agent_tables(db_path)
        self.store = MemoryStore(db_path)
        self.tools = build_tool_registry(db_path)
        self.context_builder = ContextBuilder(self.store, db_path)

    def create_conversation(self, user_id: int, title: str = "新对话") -> dict:
        return asdict(self.store.create_conversation(user_id, title))

    def list_conversations(self, user_id: int) -> list[dict]:
        self.store.repair_browser_event_artifacts(user_id)
        return [asdict(item) for item in self.store.list_conversations(user_id)]

    def list_messages(self, conversation_id: str, user_id: int) -> list[dict] | None:
        self.store.repair_browser_event_artifacts(user_id)
        if not self.store.get_conversation(conversation_id, user_id):
            return None
        return [asdict(item) for item in self.store.list_messages(conversation_id, user_id)]

    def clear_conversation(self, conversation_id: str, user_id: int) -> bool:
        return self.store.clear_conversation(conversation_id, user_id)

    def chat(
        self, user_id: int, message: str, conversation_id: str = "", context: dict | None = None
    ) -> dict:
        if conversation_id:
            conversation = self.store.get_conversation(conversation_id, user_id)
            if not conversation:
                raise ValueError("conversation_not_found")
        else:
            title = message.strip().replace("\n", " ")[:24] or "新对话"
            conversation = self.store.create_conversation(user_id, title)
            conversation_id = conversation.id

        self.store.name_conversation_from_message(conversation_id, user_id, message)

        client = get_ai_client()
        policy = (
            LocalPolicy()
            if LocalPolicy.prefers_local_routing(message) or not client.api_key
            else RemoteModelPolicy(client)
        )
        orchestrator = AgentOrchestrator(
            policy=policy,
            tools=self.tools,
            store=self.store,
            context_builder=self.context_builder,
        )
        result = orchestrator.run(user_id, conversation_id, message, entity_context=context or {})
        return {
            **asdict(result),
            "suggested_actions": result.suggested_actions or self._suggested_actions(result.tools_used),
        }

    @staticmethod
    def _suggested_actions(tools_used: list[str]) -> list[dict]:
        mapping = {
            "analyze_resume": {"label": "打开简历实验室", "page": "resume", "module": "analysis"},
            "diagnose_resume": {"label": "打开简历实验室", "page": "resume", "module": "analysis"},
            "prepare_resume_revision": {"label": "管理简历版本", "page": "resume", "module": "manage"},
            "match_job": {"label": "继续 JD 优化", "page": "resume", "module": "jd"},
            "get_interview_question": {"label": "进入面试训练", "page": "interview", "module": "mock"},
            "generate_resume_interview_questions": {"label": "进入面试训练", "page": "interview", "module": "mock"},
            "get_training_insights": {"label": "查看训练记录", "page": "interview", "module": "records"},
            "list_resumes": {"label": "管理我的简历", "page": "resume", "module": "manage"},
            "list_applications": {"label": "打开投递看板", "page": "tracker", "module": "board"},
            "get_dashboard": {"label": "查看项目总览", "page": "home", "module": ""},
        }
        actions = []
        seen = set()
        for name in tools_used:
            action = mapping.get(name)
            if not action:
                continue
            key = (action["page"], action["module"])
            if key not in seen:
                actions.append(action)
                seen.add(key)
        return actions[:3]

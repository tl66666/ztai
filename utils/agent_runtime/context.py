from __future__ import annotations

from dataclasses import dataclass, field
import re
import sqlite3

from utils.agent_runtime.memory import ClosingConnection, MemoryStore


FACT_PATTERNS = {
    "target_city": re.compile(r"(?:想去|目标城市(?:是|为)?|优先考虑)\s*([\u4e00-\u9fa5]{2,8})"),
    "target_role": re.compile(r"(?:目标岗位(?:是|为)?|想找|应聘)\s*([^，,。；;\n]{2,30})"),
    "salary_expectation": re.compile(
        r"(?:期望薪资|薪资期望|想要)\s*(\d{1,3}[kK千万]?(?:[-~到]\d{1,3}[kK千万]?)?)"
    ),
}


def extract_explicit_facts(text: str) -> dict[str, str]:
    facts = {}
    for key, pattern in FACT_PATTERNS.items():
        match = pattern.search(text or "")
        if match:
            facts[key] = match.group(1).strip()
    return facts


@dataclass(frozen=True)
class RuntimeContext:
    conversation_summary: str = ""
    recent_messages: list[dict] = field(default_factory=list)
    profile_facts: list[str] = field(default_factory=list)
    episodes: list[str] = field(default_factory=list)
    career_snapshot: str = ""

    def as_prompt(self) -> str:
        history = "\n".join(
            f"{message['role']}: {message['content']}" for message in self.recent_messages
        )
        profile = "\n".join(f"- {fact}" for fact in self.profile_facts)
        episodes = "\n".join(f"- {episode}" for episode in self.episodes)
        return (
            f"会话摘要：\n{self.conversation_summary or '暂无'}\n\n"
            f"已确认用户画像：\n{profile or '暂无'}\n\n"
            f"相关历史任务：\n{episodes or '暂无'}\n\n"
            f"实时求职数据：\n{self.career_snapshot or '暂无'}\n\n"
            f"最近对话：\n{history or '暂无'}"
        )[:12000]


class ContextBuilder:
    def __init__(self, store: MemoryStore, db_path: str, recent_limit: int = 12):
        self.store = store
        self.db_path = db_path
        self.recent_limit = recent_limit

    def needs_summary(self, conversation_id: str, user_id: int) -> bool:
        return self.store.message_count(conversation_id, user_id) > 16

    def summarize(self, conversation_id: str, user_id: int) -> str:
        messages = self.store.list_messages(conversation_id, user_id)
        if not messages:
            summary = "当前目标：暂无\n关键结论：暂无\n待办：暂无"
            until_id = None
        else:
            user_messages = [message.content for message in messages if message.role == "user"]
            assistant_messages = [message.content for message in messages if message.role == "assistant"]
            goal = user_messages[0][:180] if user_messages else "暂无"
            latest = user_messages[-1][:180] if user_messages else "暂无"
            conclusion = assistant_messages[-1][:240] if assistant_messages else "尚未形成结论"
            summary = (
                f"当前目标：{goal}\n"
                f"关键结论：{conclusion}\n"
                f"最新诉求：{latest}\n"
                "待办：继续处理最新诉求并复用已确认信息"
            )
            until_id = messages[-1].id
        self.store.save_summary(conversation_id, user_id, summary, until_id)
        return summary

    def build(self, user_id: int, conversation_id: str, query: str) -> RuntimeContext:
        conversation = self.store.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("conversation_not_found")
        messages = self.store.list_messages(conversation_id, user_id, limit=self.recent_limit)
        memories = self.store.list_memories(
            user_id,
            kind="semantic",
            statuses=("confirmed", "candidate"),
        )
        query_terms = set(re.findall(r"[A-Za-z0-9+#.]+|[\u4e00-\u9fa5]{2,}", query or ""))
        ranked = sorted(
            memories,
            key=lambda memory: (
                any(term in str(memory["value"]) for term in query_terms),
                memory["status"] == "confirmed",
                memory["confidence"],
            ),
            reverse=True,
        )[:8]
        profile_facts = [f"{memory['memory_key']}：{memory['value']}" for memory in ranked]
        episodes = self.store.list_memories(
            user_id,
            kind="episodic",
            statuses=("confirmed",),
        )
        ranked_episodes = sorted(
            episodes,
            key=lambda memory: (
                any(term in str(memory["value"]) for term in query_terms),
                memory["confidence"],
                memory["id"],
            ),
            reverse=True,
        )[:3]
        return RuntimeContext(
            conversation_summary=conversation.summary,
            recent_messages=[{"role": message.role, "content": message.content} for message in messages],
            profile_facts=profile_facts,
            episodes=[
                f"{episode['value'].get('input', '')} -> {episode['value'].get('result', '')}"
                for episode in ranked_episodes
            ],
            career_snapshot=self._career_snapshot(user_id),
        )

    def _career_snapshot(self, user_id: int) -> str:
        try:
            connection = sqlite3.connect(self.db_path, factory=ClosingConnection)
            with connection:
                resume_count = connection.execute(
                    "SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                application_count = connection.execute(
                    "SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                interview_count = connection.execute(
                    "SELECT COUNT(*) FROM interviews WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
            return f"简历 {resume_count} 份；投递 {application_count} 条；面试训练 {interview_count} 次"
        except sqlite3.Error:
            return "暂无可用业务统计"

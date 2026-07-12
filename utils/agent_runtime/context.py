from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
import sqlite3

from utils.agent_runtime.memory import ClosingConnection, MemoryStore
from utils.domain.career import CareerService


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
        return self.store.unsummarized_message_count(conversation_id, user_id) > 16

    def summarize(self, conversation_id: str, user_id: int) -> str:
        conversation = self.store.get_conversation(conversation_id, user_id)
        messages = self.store.list_unsummarized_messages(conversation_id, user_id)
        if not messages:
            summary = "当前目标：暂无\n关键结论：暂无\n待办：暂无"
            until_id = None
        else:
            user_messages = [message.content for message in messages if message.role == "user"]
            assistant_messages = [message.content for message in messages if message.role == "assistant"]
            goal = user_messages[0][:180] if user_messages else "暂无"
            latest = user_messages[-1][:180] if user_messages else "暂无"
            conclusion = assistant_messages[-1][:240] if assistant_messages else "尚未形成结论"
            previous = conversation.summary[:600] if conversation else ""
            summary = (
                f"既有摘要：{previous or '暂无'}\n"
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
        memories = self.store.search_memories(
            user_id,
            query,
            kind="semantic",
            statuses=("confirmed", "candidate"),
            limit=8,
        )
        profile_facts = [f"{memory['memory_key']}：{memory['value']}" for memory in memories]
        episodes = self.store.search_memories(
            user_id,
            query,
            kind="episodic",
            statuses=("confirmed",),
            limit=3,
        )
        return RuntimeContext(
            conversation_summary=conversation.summary,
            recent_messages=[{"role": message.role, "content": message.content} for message in messages],
            profile_facts=profile_facts,
            episodes=[
                self._episode_summary(episode["value"])
                for episode in episodes
            ],
            career_snapshot=self._career_snapshot(user_id, query),
        )

    @staticmethod
    def _episode_summary(value) -> str:
        if isinstance(value, dict):
            return f"{str(value.get('input', ''))[:240]} -> {str(value.get('result', ''))[:240]}"
        return str(value)[:500]

    def _career_snapshot(self, user_id: int, query: str = "") -> str:
        sections: list[tuple[str, object]] = []
        try:
            service: CareerService | None = CareerService(self.db_path, user_id)
        except sqlite3.Error:
            service = None

        try:
            profile = service.get_profile(user_id) if service else {}
            profile = profile or {}
            sections.append(("confirmed_profile", {
                key: profile.get(key)
                for key in ("career_direction", "target_role", "cities", "salary", "experience")
                if profile.get(key) not in (None, "", [], {})
            }))
        except (sqlite3.Error, TypeError, ValueError):
            sections.append(("confirmed_profile", {}))

        with self._business_connection() as connection:
            counts = {}
            for label, table, extra in (
                ("简历", "resumes", ""),
                ("投递", "job_applications", " AND deleted_at IS NULL"),
                ("面试训练", "interviews", ""),
            ):
                try:
                    counts[label] = connection.execute(
                        f'SELECT COUNT(*) FROM "{table}" WHERE user_id = ?{extra}', (user_id,)
                    ).fetchone()[0]
                except sqlite3.Error:
                    counts[label] = 0
            sections.append((
                "counts",
                f"简历 {counts['简历']} 份；投递 {counts['投递']} 条；面试训练 {counts['面试训练']} 次",
            ))
            try:
                opportunity_rows = connection.execute(
                    """
                    SELECT id, company, job_title, resume_id
                    FROM job_applications
                    WHERE user_id = ? AND deleted_at IS NULL
                    """,
                    (user_id,),
                ).fetchall()
                normalized_query = (query or "").casefold()
                query_tokens = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized_query))

                def opportunity_relevance(candidate: sqlite3.Row) -> int:
                    return (
                        int(str(candidate["id"]) in query_tokens)
                        + int(bool(candidate["company"]) and candidate["company"].casefold() in normalized_query)
                        + int(bool(candidate["job_title"]) and candidate["job_title"].casefold() in normalized_query)
                    )

                relevant_opportunity = max(
                    opportunity_rows, key=opportunity_relevance, default=None
                )
                selected_resume_id = (
                    relevant_opportunity["resume_id"]
                    if relevant_opportunity is not None
                    and opportunity_relevance(relevant_opportunity) > 0
                    else None
                )
                resume_rows = connection.execute(
                    """
                    SELECT id, title, version_label, target_job_title, status, updated_at
                    FROM resumes
                    WHERE user_id = ? AND COALESCE(status, 'active') != 'archived'
                    """,
                    (user_id,),
                ).fetchall()
                by_id = {candidate["id"]: candidate for candidate in resume_rows}
                row = by_id.get(selected_resume_id)
                if row is None and resume_rows:
                    row = max(
                        resume_rows,
                        key=lambda candidate: (
                            self._parsed_timestamp(candidate["updated_at"]), candidate["id"]
                        ),
                    )
                sections.append(("selected_resume", {
                    "id": row["id"], "title": row["title"], "version": row["version_label"],
                    "target": row["target_job_title"], "status": row["status"],
                    "updated": row["updated_at"],
                } if row else None))
            except sqlite3.Error:
                sections.append(("selected_resume", None))

            opportunities = []
            try:
                rows = connection.execute(
                    """
                    SELECT id, company, job_title, status, city, priority,
                           next_action_at, interview_at, deadline_at, updated_at
                    FROM job_applications
                    WHERE user_id = ? AND deleted_at IS NULL
                      AND COALESCE(status, '') NOT IN ('已拒绝', '已结束')
                    """,
                    (user_id,),
                ).fetchall()
                normalized_query = (query or "").casefold()
                query_tokens = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized_query))

                def relevance(row: sqlite3.Row) -> tuple:
                    return (
                        int(str(row["id"]) in query_tokens)
                        + int(bool(row["company"]) and row["company"].casefold() in normalized_query)
                        + int(bool(row["job_title"]) and row["job_title"].casefold() in normalized_query),
                        int(row["priority"] or 0), row["updated_at"] or "", row["id"],
                    )

                opportunities = [dict(row) for row in sorted(rows, key=relevance, reverse=True)[:5]]
            except (sqlite3.Error, TypeError, ValueError):
                opportunities = []
            sections.append(("opportunities", opportunities))

            try:
                rows = connection.execute(
                    """
                    SELECT id, application_id, title, action_type AS type, status,
                           priority, due_at, completed_at, completion_evidence, source
                    FROM action_items
                    WHERE user_id = ? AND status IN ('pending', 'in_progress')
                    ORDER BY updated_at DESC, id DESC LIMIT 8
                    """,
                    (user_id,),
                ).fetchall()
                actions = []
                for row in rows:
                    action = {
                        key: row[key]
                        for key in (
                            "id", "application_id", "title", "type", "status",
                            "priority", "due_at", "completed_at", "source",
                        )
                    }
                    if row["source"] == "domain_event" and row["completion_evidence"]:
                        action["evidence"] = str(row["completion_evidence"])[:500]
                    actions.append(action)
                sections.append(("action_items", actions))
            except sqlite3.Error:
                sections.append(("action_items", []))

            recent_events = []
            try:
                rows = connection.execute(
                    """
                    SELECT aggregate_type, aggregate_id, event_type, payload_json, occurred_at
                    FROM domain_events WHERE user_id = ?
                    ORDER BY occurred_at DESC, id DESC LIMIT 12
                    """,
                    (user_id,),
                ).fetchall()
                for row in rows:
                    outcome = {
                        "type": row["event_type"], "aggregate": row["aggregate_type"],
                        "id": row["aggregate_id"], "at": row["occurred_at"],
                    }
                    try:
                        payload = json.loads(row["payload_json"] or "{}")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        payload = {}
                    if isinstance(payload, dict):
                        for key in ("status", "score", "report_type", "answer_count", "fields"):
                            value = payload.get(key)
                            if isinstance(value, (str, int, float, bool, list)):
                                outcome[key] = value
                    recent_events.append(outcome)
                sections.append(("recent_outcomes", recent_events))
            except sqlite3.Error:
                sections.append(("recent_outcomes", []))

            sections.append(("training_match_trends", self._score_trends(connection, user_id)))

        try:
            readiness = service.calculate_readiness(user_id) if service else {}
            sections.insert(3, ("readiness", {
                key: readiness.get(key)
                for key in ("score", "label", "components", "blockers", "caps")
            }))
        except (sqlite3.Error, TypeError, ValueError):
            sections.insert(3, ("readiness", {}))

        rendered = "\n".join(
            f"{name}: {json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
            for name, value in sections
        )
        return rendered[:8000]

    def _business_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parsed_timestamp(value) -> datetime:
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    @staticmethod
    def _score_trends(connection: sqlite3.Connection, user_id: int) -> dict[str, list]:
        trends: dict[str, list] = {}
        for label, table, column in (
            ("matches", "job_matches", "match_score"),
            ("interviews", "interviews", "score"),
            ("practice", "practice_records", "score"),
        ):
            try:
                rows = connection.execute(
                    f'SELECT "{column}" FROM "{table}" WHERE user_id = ? '
                    f'AND "{column}" IS NOT NULL ORDER BY created_at DESC, id DESC LIMIT 5',
                    (user_id,),
                ).fetchall()
                trends[label] = [row[0] for row in reversed(rows) if isinstance(row[0], (int, float))]
            except sqlite3.Error:
                trends[label] = []
        return trends

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
import sqlite3

from utils.agent_runtime.memory import ClosingConnection, MemoryStore
from utils.domain.career import CareerService


def safe_text(value, maxlen: int = 500) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, bytes):
            result = value.decode("utf-8", errors="replace")
        elif isinstance(value, str):
            result = value
        elif isinstance(value, (int, float, bool)):
            result = str(value)
        else:
            result = str(value)
    except Exception:
        result = "[unreadable]"
    return result[:max(0, maxlen)]


def _json_safe(value):
    if isinstance(value, dict):
        return {
            safe_text(key, 100): _json_safe(item)
            for key, item in list(value.items())[:100]
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value[:100]]
    if isinstance(value, str):
        return safe_text(value, 1000)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return safe_text(value)


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

    def build(
        self, user_id: int, conversation_id: str, query: str,
        entity_context: dict | None = None,
    ) -> RuntimeContext:
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
            career_snapshot=self._career_snapshot(user_id, query, entity_context or {}),
        )

    @staticmethod
    def _episode_summary(value) -> str:
        if isinstance(value, dict):
            return f"{str(value.get('input', ''))[:240]} -> {str(value.get('result', ''))[:240]}"
        return str(value)[:500]

    def _career_snapshot(
        self, user_id: int, query: str = "", entity_context: dict | None = None
    ) -> str:
        requested_context = entity_context or {}
        resume_requested = "resume_id" in requested_context
        opportunity_requested = "opportunity_id" in requested_context
        entity_context = {
            key: requested_context[key]
            for key in ("module",)
            if isinstance(requested_context.get(key), str)
        }
        with self._business_connection() as context_connection:
            for key, table, extra in (
                ("resume_id", "resumes", ""),
                ("opportunity_id", "job_applications", " AND deleted_at IS NULL"),
            ):
                entity_id = requested_context.get(key)
                if not isinstance(entity_id, int) or isinstance(entity_id, bool) or entity_id <= 0:
                    continue
                owned = context_connection.execute(
                    f'SELECT 1 FROM "{table}" WHERE id = ? AND user_id = ?{extra}',
                    (entity_id, user_id),
                ).fetchone()
                if owned is not None:
                    entity_context[key] = entity_id
        sections: list[tuple[str, object]] = []
        sections.append(("ui_context", {
            key: entity_context[key]
            for key in ("module", "opportunity_id", "resume_id")
            if key in entity_context
        }))
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
            normalized_query = safe_text(query, 1000).casefold()
            query_tokens = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized_query))
            try:
                mentioned_ids = [token for token in query_tokens if token.isdigit()]
                opportunity_id = entity_context.get("opportunity_id")
                if isinstance(opportunity_id, int) and opportunity_id > 0:
                    mentioned_ids.insert(0, str(opportunity_id))
                id_order = (
                    f"id IN ({','.join('?' for _ in mentioned_ids)})"
                    if mentioned_ids else "0"
                )
                opportunity_rows = connection.execute(
                    f"""
                    SELECT id,company,job_title,status,city,priority,resume_id,
                           next_action_at,interview_at,deadline_at,updated_at
                    FROM job_applications
                    WHERE user_id = ? AND deleted_at IS NULL
                    ORDER BY
                        CASE
                            WHEN {id_order} THEN 3
                            WHEN typeof(company) = 'text' AND company != ''
                                 AND instr(?, lower(company)) > 0 THEN 2
                            WHEN typeof(job_title) = 'text' AND job_title != ''
                                 AND instr(?, lower(job_title)) > 0 THEN 1
                            ELSE 0
                        END DESC,
                        priority DESC, updated_at DESC, id DESC LIMIT 100
                    """,
                    (user_id, *mentioned_ids, normalized_query, normalized_query),
                ).fetchall()
            except sqlite3.Error:
                opportunity_rows = []

            selected_opportunity = None
            selected_opportunity_id = entity_context.get("opportunity_id")
            if isinstance(selected_opportunity_id, int) and selected_opportunity_id > 0:
                try:
                    selected_row = connection.execute(
                        """
                        SELECT id,company,job_title,status,city,salary_min,salary_max,
                               priority,resume_id,source_url,channel,next_action_at,
                               interview_at,deadline_at,applied_at,created_at,updated_at
                        FROM job_applications
                        WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                        """,
                        (selected_opportunity_id, user_id),
                    ).fetchone()
                    if selected_row is not None:
                        selected_opportunity = {
                            key: (
                                selected_row[key]
                                if isinstance(selected_row[key], (int, float))
                                else safe_text(selected_row[key], 2000 if key == "source_url" else 300)
                            )
                            for key in (
                                "id", "company", "job_title", "status", "city",
                                "salary_min", "salary_max", "priority", "resume_id",
                                "source_url", "channel", "next_action_at", "interview_at",
                                "deadline_at", "applied_at", "created_at", "updated_at",
                            )
                        }
                except (sqlite3.Error, TypeError, ValueError):
                    selected_opportunity = None
            sections.append(("selected_opportunity", selected_opportunity))

            def opportunity_relevance(candidate: sqlite3.Row) -> tuple:
                company = safe_text(candidate["company"], 300).casefold()
                job_title = safe_text(candidate["job_title"], 300).casefold()
                preferred_id = entity_context.get("opportunity_id")
                return (
                    2 * int(isinstance(preferred_id, int) and candidate["id"] == preferred_id)
                    + int(str(candidate["id"]) in query_tokens)
                    + int(bool(company) and company in normalized_query)
                    + int(bool(job_title) and job_title in normalized_query),
                    int(candidate["priority"] or 0) if isinstance(candidate["priority"], (int, float)) else 0,
                    safe_text(candidate["updated_at"], 100), candidate["id"],
                )
            try:
                relevant_opportunity = (
                    None
                    if opportunity_requested and "opportunity_id" not in entity_context
                    else max(opportunity_rows, key=opportunity_relevance, default=None)
                )
                selected_resume_id = (
                    entity_context.get("resume_id")
                    if isinstance(entity_context.get("resume_id"), int)
                    else relevant_opportunity["resume_id"]
                    if relevant_opportunity is not None
                    and opportunity_relevance(relevant_opportunity)[0] > 0
                    else None
                )
                resume_rows = connection.execute(
                    """
                    SELECT id, title, version_label, target_job_title, status, updated_at
                    FROM resumes
                    WHERE user_id = ? AND COALESCE(status, 'active') != 'archived'
                    ORDER BY id DESC LIMIT 100
                    """,
                    (user_id,),
                ).fetchall()
                by_id = {candidate["id"]: candidate for candidate in resume_rows}
                row = by_id.get(selected_resume_id)
                if row is None and resume_rows and not resume_requested:
                    row = max(
                        resume_rows,
                        key=lambda candidate: (
                            self._parsed_timestamp(candidate["updated_at"]), candidate["id"]
                        ),
                    )
                sections.append(("selected_resume", {
                    "id": row["id"], "title": safe_text(row["title"], 300),
                    "version": safe_text(row["version_label"], 100),
                    "target": safe_text(row["target_job_title"], 300),
                    "status": safe_text(row["status"], 50),
                    "updated": safe_text(row["updated_at"], 100),
                } if row else None))
            except (sqlite3.Error, TypeError, ValueError):
                sections.append(("selected_resume", None))

            opportunities = []
            try:
                active_rows = [
                    row for row in opportunity_rows
                    if safe_text(row["status"], 50) not in {"已拒绝", "已结束"}
                ]
                opportunities = []
                for row in sorted(active_rows, key=opportunity_relevance, reverse=True)[:5]:
                    opportunities.append({
                        "id": row["id"],
                        "company": safe_text(row["company"], 300),
                        "job_title": safe_text(row["job_title"], 300),
                        "status": safe_text(row["status"], 50),
                        "city": safe_text(row["city"], 200),
                        "priority": row["priority"] if isinstance(row["priority"], (int, float)) else 0,
                        "next_action_at": safe_text(row["next_action_at"], 100),
                        "interview_at": safe_text(row["interview_at"], 100),
                        "deadline_at": safe_text(row["deadline_at"], 100),
                        "updated_at": safe_text(row["updated_at"], 100),
                    })
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
                        key: (
                            row[key] if isinstance(row[key], (int, float))
                            else safe_text(row[key], 500)
                        )
                        for key in (
                            "id", "application_id", "title", "type", "status",
                            "priority", "due_at", "completed_at", "source",
                        )
                    }
                    if row["source"] == "domain_event" and row["completion_evidence"]:
                        action["evidence"] = safe_text(row["completion_evidence"], 500)
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
                        "type": safe_text(row["event_type"], 100),
                        "aggregate": safe_text(row["aggregate_type"], 100),
                        "id": safe_text(row["aggregate_id"], 100),
                        "at": safe_text(row["occurred_at"], 100),
                    }
                    try:
                        payload = json.loads(row["payload_json"] or "{}")
                    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                        payload = {}
                    if isinstance(payload, dict):
                        for key in ("status", "score", "report_type", "answer_count", "fields"):
                            value = payload.get(key)
                            if isinstance(value, (str, int, float, bool, list)):
                                outcome[key] = _json_safe(value)
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
            f"{name}: {json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
            for name, value in sections
        )
        return rendered[:8000]

    def _business_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parsed_timestamp(value) -> datetime:
        value = safe_text(value, 100)
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

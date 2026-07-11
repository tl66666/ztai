from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
import uuid

from utils.agent_runtime.models import Conversation, Message


AGENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT NOT NULL DEFAULT '',
    summary_until_message_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id)
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    slots_json TEXT NOT NULL DEFAULT '{}',
    result_summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    memory_key TEXT NOT NULL DEFAULT '',
    value_json TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    source_message_id INTEGER,
    related_entity_type TEXT,
    related_entity_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    iterations INTEGER NOT NULL DEFAULT 0,
    tools_json TEXT NOT NULL DEFAULT '[]',
    events_json TEXT NOT NULL DEFAULT '[]',
    error_code TEXT,
    latency_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_user
ON agent_conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_conversation
ON agent_messages(conversation_id, user_id, id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_conversation
ON agent_tasks(conversation_id, user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memories_user
ON agent_memories(user_id, kind, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_conversation
ON agent_runs(conversation_id, user_id, created_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def create_agent_tables(db_path: str) -> None:
    with sqlite3.connect(db_path, factory=ClosingConnection) as connection:
        connection.executescript(AGENT_SCHEMA)


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def create_conversation(self, user_id: int, title: str = "新对话") -> Conversation:
        conversation_id = uuid.uuid4().hex
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_conversations
                    (id, user_id, title, status, summary, created_at, updated_at)
                VALUES (?, ?, ?, 'active', '', ?, ?)
                """,
                (conversation_id, user_id, title.strip() or "新对话", timestamp, timestamp),
            )
        return Conversation(conversation_id, user_id, title.strip() or "新对话")

    def get_conversation(self, conversation_id: str, user_id: int) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, user_id, title, status, summary
                FROM agent_conversations WHERE id = ? AND user_id = ?
                """,
                (conversation_id, user_id),
            ).fetchone()
        if not row:
            return None
        return Conversation(row["id"], row["user_id"], row["title"], row["status"], row["summary"])

    def list_conversations(self, user_id: int) -> list[Conversation]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, title, status, summary
                FROM agent_conversations
                WHERE user_id = ? AND status = 'active'
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [
            Conversation(row["id"], row["user_id"], row["title"], row["status"], row["summary"])
            for row in rows
        ]

    def name_conversation_from_message(
        self, conversation_id: str, user_id: int, message: str
    ) -> bool:
        title = " ".join(message.strip().split())[:24]
        if not title:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agent_conversations SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND title = '新对话'
                """,
                (title, _now(), conversation_id, user_id),
            )
        return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id: str,
        user_id: int,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        timestamp = _now()
        with self._connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM agent_conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if not owned:
                raise ValueError("conversation_not_found")
            cursor = connection.execute(
                """
                INSERT INTO agent_messages
                    (conversation_id, user_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, user_id, role, content, json.dumps(metadata or {}, ensure_ascii=False), timestamp),
            )
            connection.execute(
                "UPDATE agent_conversations SET updated_at = ? WHERE id = ? AND user_id = ?",
                (timestamp, conversation_id, user_id),
            )
            message_id = cursor.lastrowid
        return Message(message_id, conversation_id, user_id, role, content, metadata or {})

    def list_messages(self, conversation_id: str, user_id: int, limit: int | None = None) -> list[Message]:
        sql = """
            SELECT id, conversation_id, user_id, role, content, metadata_json
            FROM agent_messages
            WHERE conversation_id = ? AND user_id = ?
            ORDER BY id
        """
        params: tuple = (conversation_id, user_id)
        if limit is not None:
            sql = """
                SELECT * FROM (
                    SELECT id, conversation_id, user_id, role, content, metadata_json
                    FROM agent_messages
                    WHERE conversation_id = ? AND user_id = ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id
            """
            params = (conversation_id, user_id, limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            Message(
                row["id"], row["conversation_id"], row["user_id"], row["role"], row["content"],
                json.loads(row["metadata_json"] or "{}"),
            )
            for row in rows
        ]

    def clear_conversation(self, conversation_id: str, user_id: int) -> bool:
        with self._connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM agent_conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if not owned:
                return False
            connection.execute(
                "DELETE FROM agent_messages WHERE conversation_id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
            connection.execute(
                """
                UPDATE agent_tasks SET status = 'cancelled', updated_at = ?
                WHERE conversation_id = ? AND user_id = ? AND status = 'waiting_input'
                """,
                (_now(), conversation_id, user_id),
            )
            connection.execute(
                """
                UPDATE agent_conversations
                SET summary = '', summary_until_message_id = NULL, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (_now(), conversation_id, user_id),
            )
        return True

    def message_count(self, conversation_id: str, user_id: int) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM agent_messages WHERE conversation_id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
        return int(row["count"] if row else 0)

    def unsummarized_message_count(self, conversation_id: str, user_id: int) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM agent_messages
                WHERE conversation_id = ? AND user_id = ?
                  AND id > COALESCE((
                      SELECT summary_until_message_id
                      FROM agent_conversations
                      WHERE id = ? AND user_id = ?
                  ), 0)
                """,
                (conversation_id, user_id, conversation_id, user_id),
            ).fetchone()
        return int(row["count"] if row else 0)

    def list_unsummarized_messages(self, conversation_id: str, user_id: int) -> list[Message]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, conversation_id, user_id, role, content, metadata_json
                FROM agent_messages
                WHERE conversation_id = ? AND user_id = ?
                  AND id > COALESCE((
                      SELECT summary_until_message_id
                      FROM agent_conversations
                      WHERE id = ? AND user_id = ?
                  ), 0)
                ORDER BY id
                """,
                (conversation_id, user_id, conversation_id, user_id),
            ).fetchall()
        return [
            Message(
                row["id"], row["conversation_id"], row["user_id"], row["role"], row["content"],
                json.loads(row["metadata_json"] or "{}"),
            )
            for row in rows
        ]

    def save_summary(
        self,
        conversation_id: str,
        user_id: int,
        summary: str,
        until_message_id: int | None,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agent_conversations
                SET summary = ?, summary_until_message_id = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (summary, until_message_id, _now(), conversation_id, user_id),
            )
        return cursor.rowcount > 0

    def upsert_memory(
        self,
        user_id: int,
        kind: str,
        category: str,
        memory_key: str,
        value,
        confidence: float,
        status: str,
        source_message_id: int | None = None,
    ) -> int:
        timestamp = _now()
        with self._connect() as connection:
            if status == "confirmed" and memory_key:
                connection.execute(
                    """
                    UPDATE agent_memories SET status = 'superseded', updated_at = ?
                    WHERE user_id = ? AND kind = ? AND memory_key = ? AND status = 'confirmed'
                    """,
                    (timestamp, user_id, kind, memory_key),
                )
            cursor = connection.execute(
                """
                INSERT INTO agent_memories
                    (user_id, kind, category, memory_key, value_json, confidence, status,
                     source_message_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, kind, category, memory_key,
                    json.dumps(value, ensure_ascii=False), confidence, status,
                    source_message_id, timestamp, timestamp,
                ),
            )
            return cursor.lastrowid

    def list_memories(
        self,
        user_id: int,
        kind: str | None = None,
        statuses: tuple[str, ...] = ("confirmed", "candidate"),
    ) -> list[dict]:
        clauses = ["user_id = ?"]
        params: list = [user_id]
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        placeholders = ",".join("?" for _ in statuses)
        clauses.append(f"status IN ({placeholders})")
        params.extend(statuses)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM agent_memories
                WHERE {' AND '.join(clauses)}
                ORDER BY confidence DESC, id DESC
                """,
                params,
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "category": row["category"],
                "memory_key": row["memory_key"],
                "value": json.loads(row["value_json"]),
                "confidence": row["confidence"],
                "status": row["status"],
                "source_message_id": row["source_message_id"],
            }
            for row in rows
        ]

    def create_task(
        self,
        conversation_id: str,
        user_id: int,
        task_type: str,
        slots: dict | None = None,
    ) -> str:
        task_id = uuid.uuid4().hex
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE agent_tasks SET status = 'superseded', updated_at = ?
                WHERE conversation_id = ? AND user_id = ? AND status = 'waiting_input'
                """,
                (timestamp, conversation_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO agent_tasks
                    (id, conversation_id, user_id, task_type, status, slots_json,
                     result_summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'waiting_input', ?, '', ?, ?)
                """,
                (
                    task_id,
                    conversation_id,
                    user_id,
                    task_type,
                    json.dumps(slots or {}, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )
        return task_id

    def get_active_task(self, conversation_id: str, user_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM agent_tasks
                WHERE conversation_id = ? AND user_id = ? AND status = 'waiting_input'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (conversation_id, user_id),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "task_type": row["task_type"],
            "status": row["status"],
            "slots": json.loads(row["slots_json"] or "{}"),
        }

    def update_task(
        self,
        task_id: str,
        user_id: int,
        status: str,
        slots: dict | None = None,
        result_summary: str = "",
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agent_tasks
                SET status = ?, slots_json = COALESCE(?, slots_json),
                    result_summary = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    status,
                    json.dumps(slots, ensure_ascii=False) if slots is not None else None,
                    result_summary,
                    _now(),
                    task_id,
                    user_id,
                ),
            )
        return cursor.rowcount > 0

    def record_run(
        self,
        conversation_id: str,
        user_id: int,
        status: str,
        iterations: int,
        tools: list[str],
        events: list[dict],
        provider: str = "local",
        model: str = "local-policy",
        task_id: str | None = None,
        error_code: str = "",
        latency_ms: int = 0,
    ) -> str:
        run_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs
                    (id, conversation_id, user_id, task_id, status, provider, model,
                     iterations, tools_json, events_json, error_code, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, conversation_id, user_id, task_id, status, provider, model,
                    iterations, json.dumps(tools, ensure_ascii=False),
                    json.dumps(events, ensure_ascii=False), error_code or None,
                    latency_ms, _now(),
                ),
            )
        return run_id

    def run_count(self, conversation_id: str, user_id: int) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM agent_runs WHERE conversation_id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
        return int(row["count"] if row else 0)

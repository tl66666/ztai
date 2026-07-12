from __future__ import annotations

from datetime import datetime, timezone
import json
import re
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


def _search_terms(text: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", (text or "").casefold()):
        terms.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 2:
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
    return list(dict.fromkeys(terms))


def _normalized_value(value) -> str:
    def normalize(item):
        if isinstance(item, str):
            return " ".join(item.casefold().split())
        if isinstance(item, dict):
            return {str(key): normalize(item[key]) for key in sorted(item, key=str)}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        return item

    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def create_agent_tables(db_path: str) -> None:
    with sqlite3.connect(db_path, factory=ClosingConnection) as connection:
        connection.executescript(AGENT_SCHEMA)
        try:
            connection.executescript(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS agent_memories_fts USING fts5(
                    searchable, user_id UNINDEXED, memory_id UNINDEXED
                );
                CREATE TRIGGER IF NOT EXISTS agent_memories_fts_insert
                AFTER INSERT ON agent_memories BEGIN
                    INSERT INTO agent_memories_fts(rowid, searchable, user_id, memory_id)
                    VALUES (
                        new.id,
                        new.category || ' ' || new.memory_key || ' ' || new.value_json || ' ' ||
                        COALESCE(new.related_entity_type, '') || ' ' || COALESCE(new.related_entity_id, ''),
                        new.user_id,
                        new.id
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS agent_memories_fts_delete
                AFTER DELETE ON agent_memories BEGIN
                    DELETE FROM agent_memories_fts WHERE rowid = old.id;
                END;
                CREATE TRIGGER IF NOT EXISTS agent_memories_fts_update
                AFTER UPDATE ON agent_memories BEGIN
                    DELETE FROM agent_memories_fts WHERE rowid = old.id;
                    INSERT INTO agent_memories_fts(rowid, searchable, user_id, memory_id)
                    VALUES (
                        new.id,
                        new.category || ' ' || new.memory_key || ' ' || new.value_json || ' ' ||
                        COALESCE(new.related_entity_type, '') || ' ' || COALESCE(new.related_entity_id, ''),
                        new.user_id,
                        new.id
                    );
                END;
                """
            )
            connection.execute("DELETE FROM agent_memories_fts")
            connection.execute(
                """
                INSERT INTO agent_memories_fts(rowid, searchable, user_id, memory_id)
                SELECT id,
                       category || ' ' || memory_key || ' ' || value_json || ' ' ||
                       COALESCE(related_entity_type, '') || ' ' || COALESCE(related_entity_id, ''),
                       user_id, id
                FROM agent_memories
                """
            )
        except sqlite3.OperationalError:
            pass


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
        related_entity_type: str | None = None,
        related_entity_id: str | int | None = None,
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
                     source_message_id, related_entity_type, related_entity_id,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, kind, category, memory_key,
                    json.dumps(value, ensure_ascii=False), confidence, status,
                    source_message_id, related_entity_type,
                    str(related_entity_id) if related_entity_id is not None else None,
                    timestamp, timestamp,
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
            self._memory_from_row(row)
            for row in rows
        ]

    def fts_available(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'agent_memories_fts'"
                ).fetchone() is not None
        except sqlite3.OperationalError:
            return False

    def _fts_matches(self, connection: sqlite3.Connection, query: str, user_id: int) -> dict[int, float]:
        terms = _search_terms(query)
        if not terms:
            return {}
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms[:12])
        rows = connection.execute(
            """
            SELECT memory_id, bm25(agent_memories_fts) AS relevance
            FROM agent_memories_fts
            WHERE agent_memories_fts MATCH ? AND user_id = ?
            ORDER BY relevance LIMIT 100
            """,
            (expression, user_id),
        ).fetchall()
        return {int(row["memory_id"]): -float(row["relevance"]) for row in rows}

    def search_memories(
        self,
        user_id: int,
        query: str,
        kind: str | None = None,
        statuses: tuple[str, ...] = ("confirmed", "candidate"),
        limit: int = 8,
    ) -> list[dict]:
        if limit <= 0 or not statuses:
            return []
        clauses = ["user_id = ?"]
        params: list = [user_id]
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        clauses.append(f"status IN ({','.join('?' for _ in statuses)})")
        params.extend(statuses)
        normalized = " ".join((query or "").casefold().split())
        terms = _search_terms(normalized)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM agent_memories WHERE {' AND '.join(clauses)}",
                params,
            ).fetchall()
            try:
                fts_scores = self._fts_matches(connection, query, user_id)
            except sqlite3.OperationalError:
                fts_scores = {}

        def rank(row: sqlite3.Row) -> tuple:
            searchable = " ".join(
                str(row[key] or "")
                for key in ("category", "memory_key", "value_json", "related_entity_type", "related_entity_id")
            ).casefold()
            entity_exact = bool(
                row["related_entity_id"]
                and str(row["related_entity_id"]).casefold() in terms
                and (not row["related_entity_type"] or str(row["related_entity_type"]).casefold() in normalized)
            )
            exact_field = any(
                term and term in terms
                for term in (str(row["category"] or "").casefold(), str(row["memory_key"] or "").casefold())
            )
            searchable_terms = set(_search_terms(searchable))
            overlap_signature = tuple(term in searchable_terms for term in terms)
            overlap_hits = len(set(terms) & searchable_terms)
            overlap_weight = sum(
                len(terms) - index
                for index, term in enumerate(terms)
                if term in searchable_terms
            )
            substring_hits = sum(term in searchable for term in terms)
            reverse_hit = any(
                len(value) >= 2 and value in normalized
                for value in (
                    str(row["category"] or "").casefold(),
                    str(row["memory_key"] or "").casefold(),
                    str(row["value_json"] or "").strip('"').casefold(),
                    str(row["related_entity_id"] or "").casefold(),
                )
            )
            return (
                entity_exact,
                exact_field,
                reverse_hit,
                overlap_signature,
                overlap_weight,
                overlap_hits,
                row["id"] in fts_scores,
                fts_scores.get(row["id"], 0.0),
                substring_hits,
                row["status"] == "confirmed",
                float(row["confidence"]),
                row["updated_at"] or "",
                row["id"],
            )

        deduplicated: dict[tuple, sqlite3.Row] = {}
        for row in rows:
            parsed = self._memory_from_row(row)
            identity = (
                row["kind"], row["category"], row["memory_key"],
                _normalized_value(parsed["value"]),
            ) if row["kind"] == "semantic" else (
                row["kind"], _normalized_value(parsed["value"]),
                row["related_entity_type"] or "", row["related_entity_id"] or "",
            )
            incumbent = deduplicated.get(identity)
            quality = (
                row["status"] == "confirmed", float(row["confidence"]),
                row["updated_at"] or "", row["id"],
            )
            if incumbent is None or quality > (
                incumbent["status"] == "confirmed", float(incumbent["confidence"]),
                incumbent["updated_at"] or "", incumbent["id"],
            ):
                deduplicated[identity] = row
        candidate_rows = list(deduplicated.values())

        relevant = [
            row for row in candidate_rows
            if not terms or row["id"] in fts_scores or any(
                term in " ".join(str(row[key] or "") for key in (
                    "category", "memory_key", "value_json", "related_entity_type", "related_entity_id"
                )).casefold()
                for term in terms
            ) or any(
                len(value) >= 2 and value in normalized
                for value in (
                    str(row["category"] or "").casefold(),
                    str(row["memory_key"] or "").casefold(),
                    str(row["value_json"] or "").strip('"').casefold(),
                    str(row["related_entity_id"] or "").casefold(),
                )
            )
        ]
        relevant_ids = {row["id"] for row in relevant}
        ordered = sorted(relevant, key=rank, reverse=True)
        if len(ordered) < limit:
            ordered.extend(
                sorted(
                    (row for row in candidate_rows if row["id"] not in relevant_ids),
                    key=rank,
                    reverse=True,
                )[: limit - len(ordered)]
            )
        return [self._memory_from_row(row) for row in ordered[:limit]]

    def delete_memory(self, user_id: int, memory_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM agent_memories WHERE id = ? AND user_id = ?", (memory_id, user_id)
            )
        return cursor.rowcount > 0

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> dict:
        try:
            value = json.loads(row["value_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            value = str(row["value_json"] or "")[:500]
        return {
            "id": row["id"], "user_id": row["user_id"], "kind": row["kind"],
            "category": row["category"], "memory_key": row["memory_key"], "value": value,
            "confidence": row["confidence"], "status": row["status"],
            "source_message_id": row["source_message_id"],
            "related_entity_type": row["related_entity_type"],
            "related_entity_id": row["related_entity_id"],
        }

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

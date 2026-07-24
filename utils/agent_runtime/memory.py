from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from backend.adapters.persistence.sqlalchemy.agent_memory_store import (
    SqlAlchemyAgentMemoryStore,
)
from backend.adapters.persistence.sqlalchemy.agent_session import (
    AgentSessionProvider,
    SessionFactory,
)
from utils.agent_runtime.models import Conversation, Message

MAX_SEARCH_CANDIDATES = 500
MAX_EXACT_QUERY_TOKENS = 24
MAX_SEARCH_TERMS = 24
BROWSER_EVENT_ARTIFACTS = frozenset(
    {
        "[object Event]",
        "[object MouseEvent]",
        "[object PointerEvent]",
    }
)


def is_browser_event_artifact(value: object) -> bool:
    return isinstance(value, str) and value.strip() in BROWSER_EVENT_ARTIFACTS


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _search_terms(text: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", (text or "").casefold()):
        terms.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 2:
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
    terms = list(dict.fromkeys(terms))
    if len(terms) <= MAX_SEARCH_TERMS:
        return terms

    selected = {0, len(terms) - 1}
    latin_indexes = [index for index, term in enumerate(terms) if re.fullmatch(r"[a-z0-9]+", term)]
    for index in [*latin_indexes[:4], *latin_indexes[-4:]]:
        selected.add(index)
    for index in range(min(6, len(terms))):
        selected.add(index)
    for index in range(max(0, len(terms) - 6), len(terms)):
        selected.add(index)
    remaining = MAX_SEARCH_TERMS - len(selected)
    if remaining > 0:
        step = (len(terms) - 1) / (remaining + 1)
        for offset in range(1, remaining + 1):
            selected.add(round(step * offset))
    return [terms[index] for index in sorted(selected)[:MAX_SEARCH_TERMS]]


def _normalized_value(value) -> str:
    def normalize(item):
        if isinstance(item, str):
            return " ".join(item.casefold().split())
        if isinstance(item, dict):
            return {str(key): normalize(item[key]) for key in sorted(item, key=str)}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        return item

    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def create_agent_tables(
    db_path: str,
    *,
    session_factory: SessionFactory | None = None,
) -> None:
    """Compatibility helper for isolated callers.

    Production startup owns schema migrations through Alembic; tests that create
    only the agent tables can continue to use this small SQLAlchemy metadata path.
    """

    sessions = AgentSessionProvider(db_path, session_factory=session_factory)
    try:
        SqlAlchemyAgentMemoryStore(sessions).create_tables()
    finally:
        sessions.dispose()


class MemoryStore:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        session_factory: SessionFactory | None = None,
    ):
        self.db_path = db_path or ""
        self._sessions = AgentSessionProvider(
            db_path,
            session_factory=session_factory,
        )
        self._persistence = SqlAlchemyAgentMemoryStore(self._sessions)
        self._last_search_candidate_count = 0
        self._last_fallback_scan_count = 0

    def create_conversation(self, user_id: int, title: str = "新对话") -> Conversation:
        conversation_id = uuid.uuid4().hex
        timestamp = _now()
        safe_title = title.strip() if isinstance(title, str) else ""
        if not safe_title or is_browser_event_artifact(safe_title):
            safe_title = "新对话"
        self._persistence.create_conversation(
            {
                "id": conversation_id,
                "user_id": user_id,
                "title": safe_title,
                "status": "active",
                "summary": "",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        return Conversation(conversation_id, user_id, safe_title)

    def get_conversation(self, conversation_id: str, user_id: int) -> Conversation | None:
        row = self._persistence.get_conversation(conversation_id, user_id)
        if not row:
            return None
        return Conversation(
            row["id"],
            row["user_id"],
            row["title"],
            row["status"],
            row["summary"],
        )

    def list_conversations(self, user_id: int) -> list[Conversation]:
        return [
            Conversation(
                row["id"],
                row["user_id"],
                row["title"],
                row["status"],
                row["summary"],
            )
            for row in self._persistence.list_conversations(user_id)
        ]

    def name_conversation_from_message(
        self,
        conversation_id: str,
        user_id: int,
        message: str,
    ) -> bool:
        title = " ".join(message.strip().split())[:24]
        if not title or is_browser_event_artifact(title):
            return False
        return self._persistence.name_conversation(
            conversation_id,
            user_id,
            title,
            _now(),
        )

    def repair_browser_event_artifacts(self, user_id: int) -> None:
        self._persistence.repair_browser_event_artifacts(
            user_id,
            tuple(BROWSER_EVENT_ARTIFACTS),
            _now(),
        )

    def add_message(
        self,
        conversation_id: str,
        user_id: int,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        metadata = metadata or {}
        message_id = self._persistence.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata, ensure_ascii=False),
            created_at=_now(),
        )
        return Message(message_id, conversation_id, user_id, role, content, metadata)

    def list_messages(
        self,
        conversation_id: str,
        user_id: int,
        limit: int | None = None,
    ) -> list[Message]:
        return [
            self._message_from_row(row)
            for row in self._persistence.list_messages(
                conversation_id,
                user_id,
                limit,
            )
        ]

    def clear_conversation(self, conversation_id: str, user_id: int) -> bool:
        return self._persistence.clear_conversation(
            conversation_id,
            user_id,
            _now(),
        )

    def message_count(self, conversation_id: str, user_id: int) -> int:
        return self._persistence.message_count(conversation_id, user_id)

    def unsummarized_message_count(self, conversation_id: str, user_id: int) -> int:
        after_id = self._persistence.summary_until_message_id(conversation_id, user_id)
        return len(
            self._persistence.list_messages(
                conversation_id,
                user_id,
                after_id=after_id,
            )
        )

    def list_unsummarized_messages(
        self,
        conversation_id: str,
        user_id: int,
    ) -> list[Message]:
        after_id = self._persistence.summary_until_message_id(conversation_id, user_id)
        return [
            self._message_from_row(row)
            for row in self._persistence.list_messages(
                conversation_id,
                user_id,
                after_id=after_id,
            )
        ]

    def save_summary(
        self,
        conversation_id: str,
        user_id: int,
        summary: str,
        until_message_id: int | None,
    ) -> bool:
        return self._persistence.save_summary(
            conversation_id,
            user_id,
            summary,
            until_message_id,
            _now(),
        )

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
        normalized_entity_id = str(related_entity_id) if related_entity_id is not None else None
        return self._persistence.insert_memory(
            {
                "user_id": user_id,
                "kind": kind,
                "category": category,
                "memory_key": memory_key,
                "value_json": json.dumps(value, ensure_ascii=False),
                "confidence": confidence,
                "status": status,
                "source_message_id": source_message_id,
                "related_entity_type": related_entity_type,
                "related_entity_id": normalized_entity_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            supersede_confirmed=status == "confirmed" and bool(memory_key),
        )

    def list_memories(
        self,
        user_id: int,
        kind: str | None = None,
        statuses: tuple[str, ...] = ("confirmed", "candidate"),
    ) -> list[dict]:
        return [
            self._memory_from_row(row)
            for row in self._persistence.list_memories(user_id, kind, statuses)
        ]

    def fts_available(self) -> bool:
        return self._sessions.dialect_name == "postgresql"

    def _fts_matches(
        self,
        query: str,
        user_id: int,
        limit: int = 160,
        kind: str | None = None,
        statuses: tuple[str, ...] = ("confirmed", "candidate"),
    ) -> dict[int, float]:
        return self._persistence.postgres_fts_scores(
            query,
            user_id,
            limit,
            kind,
            statuses,
        )

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
        normalized = " ".join((query or "").casefold().split())
        terms = _search_terms(normalized)
        candidate_cap = max(50, min(MAX_SEARCH_CANDIDATES, limit * 20))
        primary_budget = max(8, candidate_cap * 3 // 5)
        try:
            fts_scores = self._fts_matches(
                query,
                user_id,
                primary_budget,
                kind,
                statuses,
            )
        except Exception:
            fts_scores = {}
        raw_tokens = re.findall(
            r"[a-z0-9_]+|[\u4e00-\u9fff]+",
            normalized,
        )[:MAX_EXACT_QUERY_TOKENS]
        rows, fallback_scan_count = self._persistence.search_candidates(
            user_id=user_id,
            normalized_query=normalized,
            terms=terms,
            raw_tokens=raw_tokens,
            kind=kind,
            statuses=statuses,
            candidate_cap=candidate_cap,
            fts_scores=fts_scores,
        )
        self._last_search_candidate_count = len(rows)
        self._last_fallback_scan_count = fallback_scan_count

        def rank(row: Mapping[str, object]) -> tuple:
            searchable = " ".join(
                str(row[key] or "")
                for key in (
                    "category",
                    "memory_key",
                    "value_json",
                    "related_entity_type",
                    "related_entity_id",
                )
            ).casefold()
            entity_exact = bool(
                row["related_entity_id"]
                and str(row["related_entity_id"]).casefold() in terms
                and (
                    not row["related_entity_type"]
                    or str(row["related_entity_type"]).casefold() in normalized
                )
            )
            normalized_value_text = str(row["value_json"] or "").strip('"').casefold()
            value_query_hit = bool(
                len(normalized_value_text) >= 2 and normalized_value_text in normalized
            )
            exact_field = any(
                term and term in terms
                for term in (
                    str(row["category"] or "").casefold(),
                    str(row["memory_key"] or "").casefold(),
                )
            )
            searchable_terms = set(_search_terms(searchable))
            overlap_signature = tuple(term in searchable_terms for term in terms)
            overlap_hits = len(set(terms) & searchable_terms)
            overlap_weight = sum(
                len(terms) - index for index, term in enumerate(terms) if term in searchable_terms
            )
            substring_hits = sum(term in searchable for term in terms)
            reverse_hit = any(
                len(value) >= 2 and value in normalized
                for value in (
                    str(row["category"] or "").casefold(),
                    str(row["memory_key"] or "").casefold(),
                    normalized_value_text,
                    str(row["related_entity_id"] or "").casefold(),
                )
            )
            row_id = int(row["id"])
            return (
                entity_exact,
                value_query_hit,
                exact_field,
                reverse_hit,
                overlap_signature,
                overlap_weight,
                overlap_hits,
                row_id in fts_scores,
                fts_scores.get(row_id, 0.0),
                substring_hits,
                row["status"] == "confirmed",
                float(row["confidence"]),
                row["updated_at"] or "",
                row_id,
            )

        deduplicated: dict[tuple, Mapping[str, object]] = {}
        for row in rows:
            parsed = self._memory_from_row(row)
            if row["kind"] == "semantic":
                identity = (
                    row["kind"],
                    row["category"],
                    row["memory_key"],
                    _normalized_value(parsed["value"]),
                    row["related_entity_type"] or "",
                    row["related_entity_id"] or "",
                )
            else:
                identity = (
                    row["kind"],
                    _normalized_value(parsed["value"]),
                    row["related_entity_type"] or "",
                    row["related_entity_id"] or "",
                )
            incumbent = deduplicated.get(identity)
            quality = (
                row["status"] == "confirmed",
                float(row["confidence"]),
                row["updated_at"] or "",
                int(row["id"]),
            )
            if incumbent is None or quality > (
                incumbent["status"] == "confirmed",
                float(incumbent["confidence"]),
                incumbent["updated_at"] or "",
                int(incumbent["id"]),
            ):
                deduplicated[identity] = row
        candidate_rows = list(deduplicated.values())
        relevant = [
            row
            for row in candidate_rows
            if not terms
            or int(row["id"]) in fts_scores
            or any(
                term
                in " ".join(
                    str(row[key] or "")
                    for key in (
                        "category",
                        "memory_key",
                        "value_json",
                        "related_entity_type",
                        "related_entity_id",
                    )
                ).casefold()
                for term in terms
            )
            or any(
                len(value) >= 2 and value in normalized
                for value in (
                    str(row["category"] or "").casefold(),
                    str(row["memory_key"] or "").casefold(),
                    str(row["value_json"] or "").strip('"').casefold(),
                    str(row["related_entity_id"] or "").casefold(),
                )
            )
        ]
        relevant_ids = {int(row["id"]) for row in relevant}
        ordered = sorted(relevant, key=rank, reverse=True)
        if len(ordered) < limit:
            ordered.extend(
                sorted(
                    (row for row in candidate_rows if int(row["id"]) not in relevant_ids),
                    key=rank,
                    reverse=True,
                )[: limit - len(ordered)]
            )
        return [self._memory_from_row(row) for row in ordered[:limit]]

    def delete_memory(self, user_id: int, memory_id: int) -> bool:
        return self._persistence.delete_memory(user_id, memory_id)

    def create_task(
        self,
        conversation_id: str,
        user_id: int,
        task_type: str,
        slots: dict | None = None,
    ) -> str:
        task_id = uuid.uuid4().hex
        timestamp = _now()
        self._persistence.create_task(
            {
                "id": task_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "task_type": task_type,
                "status": "waiting_input",
                "slots_json": json.dumps(slots or {}, ensure_ascii=False),
                "result_summary": "",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        return task_id

    def get_active_task(self, conversation_id: str, user_id: int) -> dict | None:
        row = self._persistence.get_active_task(conversation_id, user_id)
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
        return self._persistence.update_task(
            task_id,
            user_id,
            status=status,
            slots_json=(json.dumps(slots, ensure_ascii=False) if slots is not None else None),
            result_summary=result_summary,
            updated_at=_now(),
        )

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
        self._persistence.record_run(
            {
                "id": run_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "task_id": task_id,
                "status": status,
                "provider": provider,
                "model": model,
                "iterations": iterations,
                "tools_json": json.dumps(tools, ensure_ascii=False),
                "events_json": json.dumps(events, ensure_ascii=False),
                "error_code": error_code or None,
                "latency_ms": latency_ms,
                "created_at": _now(),
            }
        )
        return run_id

    def run_count(self, conversation_id: str, user_id: int) -> int:
        return self._persistence.run_count(conversation_id, user_id)

    @staticmethod
    def _message_from_row(row: Mapping[str, object]) -> Message:
        return Message(
            int(row["id"]),
            str(row["conversation_id"]),
            int(row["user_id"]),
            str(row["role"]),
            str(row["content"]),
            json.loads(str(row["metadata_json"] or "{}")),
        )

    @staticmethod
    def _memory_from_row(row: Mapping[str, object]) -> dict:
        try:
            value = json.loads(str(row["value_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            value = str(row["value_json"] or "")[:500]
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "kind": row["kind"],
            "category": row["category"],
            "memory_key": row["memory_key"],
            "value": value,
            "confidence": row["confidence"],
            "status": row["status"],
            "source_message_id": row["source_message_id"],
            "related_entity_type": row["related_entity_type"],
            "related_entity_id": row["related_entity_id"],
        }

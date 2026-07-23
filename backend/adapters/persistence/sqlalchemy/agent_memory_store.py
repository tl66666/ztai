from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import case, delete, func, insert, literal, or_, select, update

from .agent_models import (
    agent_conversations,
    agent_memories,
    agent_messages,
    agent_runs,
    agent_tasks,
)
from .agent_session import AgentSessionProvider
from .base import metadata

AGENT_TABLES = (
    agent_conversations,
    agent_messages,
    agent_tasks,
    agent_memories,
    agent_runs,
)


class SqlAlchemyAgentMemoryStore:
    """SQLAlchemy adapter for conversations, durable memory, tasks, and runs."""

    def __init__(self, sessions: AgentSessionProvider):
        self.sessions = sessions

    def create_tables(self) -> None:
        bind = self.sessions.session_factory.kw.get("bind")
        if bind is None:
            with self.sessions.session_factory() as session:
                bind = session.get_bind()
        metadata.create_all(bind, tables=list(AGENT_TABLES))

    def create_conversation(self, values: Mapping[str, Any]) -> None:
        with self.sessions.session() as session:
            session.execute(insert(agent_conversations).values(**values))

    def get_conversation(self, conversation_id: str, user_id: int) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            return (
                session.execute(
                    select(
                        agent_conversations.c.id,
                        agent_conversations.c.user_id,
                        agent_conversations.c.title,
                        agent_conversations.c.status,
                        agent_conversations.c.summary,
                    ).where(
                        agent_conversations.c.id == conversation_id,
                        agent_conversations.c.user_id == user_id,
                    )
                )
                .mappings()
                .first()
            )

    def list_conversations(self, user_id: int) -> list[Mapping[str, Any]]:
        with self.sessions.session() as session:
            return list(
                session.execute(
                    select(
                        agent_conversations.c.id,
                        agent_conversations.c.user_id,
                        agent_conversations.c.title,
                        agent_conversations.c.status,
                        agent_conversations.c.summary,
                    )
                    .where(
                        agent_conversations.c.user_id == user_id,
                        agent_conversations.c.status == "active",
                    )
                    .order_by(agent_conversations.c.updated_at.desc())
                ).mappings()
            )

    def name_conversation(
        self,
        conversation_id: str,
        user_id: int,
        title: str,
        updated_at: str,
    ) -> bool:
        with self.sessions.session() as session:
            result = session.execute(
                update(agent_conversations)
                .where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                    agent_conversations.c.title == "新对话",
                )
                .values(title=title, updated_at=updated_at)
            )
            return result.rowcount > 0

    def repair_browser_event_artifacts(
        self,
        user_id: int,
        artifacts: Sequence[str],
        updated_at: str,
    ) -> None:
        with self.sessions.session() as session:
            conversations = list(
                session.execute(
                    select(agent_conversations.c.id, agent_conversations.c.title).where(
                        agent_conversations.c.user_id == user_id
                    )
                ).mappings()
            )
            for conversation in conversations:
                conversation_id = str(conversation["id"])
                if conversation["title"] in artifacts:
                    session.execute(
                        update(agent_conversations)
                        .where(
                            agent_conversations.c.id == conversation_id,
                            agent_conversations.c.user_id == user_id,
                        )
                        .values(title="新对话", updated_at=updated_at)
                    )
                rows = list(
                    session.execute(
                        select(
                            agent_messages.c.id,
                            agent_messages.c.role,
                            agent_messages.c.content,
                        )
                        .where(
                            agent_messages.c.conversation_id == conversation_id,
                            agent_messages.c.user_id == user_id,
                        )
                        .order_by(agent_messages.c.id)
                    ).mappings()
                )
                delete_ids: list[int] = []
                for index, row in enumerate(rows):
                    if row["role"] != "user" or row["content"] not in artifacts:
                        continue
                    delete_ids.append(int(row["id"]))
                    next_index = index + 1
                    while next_index < len(rows) and rows[next_index]["role"] != "user":
                        delete_ids.append(int(rows[next_index]["id"]))
                        next_index += 1
                if not delete_ids:
                    continue
                session.execute(
                    delete(agent_messages).where(
                        agent_messages.c.id.in_(delete_ids),
                        agent_messages.c.user_id == user_id,
                    )
                )
                session.execute(
                    update(agent_conversations)
                    .where(
                        agent_conversations.c.id == conversation_id,
                        agent_conversations.c.user_id == user_id,
                    )
                    .values(
                        summary="",
                        summary_until_message_id=None,
                        updated_at=updated_at,
                    )
                )

    def add_message(
        self,
        *,
        conversation_id: str,
        user_id: int,
        role: str,
        content: str,
        metadata_json: str,
        created_at: str,
    ) -> int:
        with self.sessions.session() as session:
            owned = session.execute(
                select(agent_conversations.c.id).where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
            ).first()
            if not owned:
                raise ValueError("conversation_not_found")
            result = session.execute(
                insert(agent_messages)
                .values(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    metadata_json=metadata_json,
                    created_at=created_at,
                )
                .returning(agent_messages.c.id)
            )
            message_id = int(result.scalar_one())
            session.execute(
                update(agent_conversations)
                .where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
                .values(updated_at=created_at)
            )
            return message_id

    def list_messages(
        self,
        conversation_id: str,
        user_id: int,
        limit: int | None = None,
        *,
        after_id: int | None = None,
    ) -> list[Mapping[str, Any]]:
        statement = select(
            agent_messages.c.id,
            agent_messages.c.conversation_id,
            agent_messages.c.user_id,
            agent_messages.c.role,
            agent_messages.c.content,
            agent_messages.c.metadata_json,
        ).where(
            agent_messages.c.conversation_id == conversation_id,
            agent_messages.c.user_id == user_id,
        )
        if after_id is not None:
            statement = statement.where(agent_messages.c.id > after_id)
        if limit is not None:
            statement = statement.order_by(agent_messages.c.id.desc()).limit(limit)
        else:
            statement = statement.order_by(agent_messages.c.id)
        with self.sessions.session() as session:
            rows = list(session.execute(statement).mappings())
        if limit is not None:
            rows.reverse()
        return rows

    def clear_conversation(self, conversation_id: str, user_id: int, updated_at: str) -> bool:
        with self.sessions.session() as session:
            owned = session.execute(
                select(agent_conversations.c.id).where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
            ).first()
            if not owned:
                return False
            session.execute(
                delete(agent_messages).where(
                    agent_messages.c.conversation_id == conversation_id,
                    agent_messages.c.user_id == user_id,
                )
            )
            session.execute(
                update(agent_tasks)
                .where(
                    agent_tasks.c.conversation_id == conversation_id,
                    agent_tasks.c.user_id == user_id,
                    agent_tasks.c.status == "waiting_input",
                )
                .values(status="cancelled", updated_at=updated_at)
            )
            session.execute(
                update(agent_conversations)
                .where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
                .values(
                    summary="",
                    summary_until_message_id=None,
                    updated_at=updated_at,
                )
            )
            return True

    def message_count(self, conversation_id: str, user_id: int) -> int:
        with self.sessions.session() as session:
            return int(
                session.execute(
                    select(func.count())
                    .select_from(agent_messages)
                    .where(
                        agent_messages.c.conversation_id == conversation_id,
                        agent_messages.c.user_id == user_id,
                    )
                ).scalar_one()
            )

    def summary_until_message_id(self, conversation_id: str, user_id: int) -> int:
        with self.sessions.session() as session:
            value = session.execute(
                select(agent_conversations.c.summary_until_message_id).where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
            ).scalar_one_or_none()
        return int(value or 0)

    def save_summary(
        self,
        conversation_id: str,
        user_id: int,
        summary: str,
        until_message_id: int | None,
        updated_at: str,
    ) -> bool:
        with self.sessions.session() as session:
            result = session.execute(
                update(agent_conversations)
                .where(
                    agent_conversations.c.id == conversation_id,
                    agent_conversations.c.user_id == user_id,
                )
                .values(
                    summary=summary,
                    summary_until_message_id=until_message_id,
                    updated_at=updated_at,
                )
            )
            return result.rowcount > 0

    def insert_memory(
        self,
        values: Mapping[str, Any],
        *,
        supersede_confirmed: bool,
    ) -> int:
        with self.sessions.session() as session:
            if supersede_confirmed:
                session.execute(
                    update(agent_memories)
                    .where(
                        agent_memories.c.user_id == values["user_id"],
                        agent_memories.c.kind == values["kind"],
                        agent_memories.c.memory_key == values["memory_key"],
                        agent_memories.c.status == "confirmed",
                        agent_memories.c.related_entity_type.is_(values["related_entity_type"]),
                        agent_memories.c.related_entity_id.is_(values["related_entity_id"]),
                    )
                    .values(status="superseded", updated_at=values["updated_at"])
                )
            result = session.execute(
                insert(agent_memories).values(**values).returning(agent_memories.c.id)
            )
            return int(result.scalar_one())

    def list_memories(
        self,
        user_id: int,
        kind: str | None,
        statuses: Sequence[str],
    ) -> list[Mapping[str, Any]]:
        statement = select(agent_memories).where(
            agent_memories.c.user_id == user_id,
            agent_memories.c.status.in_(statuses),
        )
        if kind:
            statement = statement.where(agent_memories.c.kind == kind)
        statement = statement.order_by(
            agent_memories.c.confidence.desc(), agent_memories.c.id.desc()
        )
        with self.sessions.session() as session:
            return list(session.execute(statement).mappings())

    def postgres_fts_scores(
        self,
        query: str,
        user_id: int,
        limit: int,
        kind: str | None,
        statuses: Sequence[str],
    ) -> dict[int, float]:
        if self.sessions.dialect_name != "postgresql":
            raise NotImplementedError("native full text search requires PostgreSQL")
        document = func.to_tsvector(
            literal("simple"),
            func.concat_ws(
                " ",
                func.coalesce(agent_memories.c.category, ""),
                func.coalesce(agent_memories.c.memory_key, ""),
                func.coalesce(agent_memories.c.value_json, ""),
                func.coalesce(agent_memories.c.related_entity_type, ""),
                func.coalesce(agent_memories.c.related_entity_id, ""),
            ),
        )
        search_query = func.plainto_tsquery(literal("simple"), query)
        rank = func.ts_rank(document, search_query).label("relevance")
        statement = (
            select(agent_memories.c.id.label("memory_id"), rank)
            .where(
                agent_memories.c.user_id == user_id,
                agent_memories.c.status.in_(statuses),
                document.op("@@")(search_query),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        if kind:
            statement = statement.where(agent_memories.c.kind == kind)
        with self.sessions.session() as session:
            rows = session.execute(statement).mappings()
            return {int(row["memory_id"]): float(row["relevance"] or 0.0) for row in rows}

    def search_candidates(
        self,
        *,
        user_id: int,
        normalized_query: str,
        terms: Sequence[str],
        raw_tokens: Sequence[str],
        kind: str | None,
        statuses: Sequence[str],
        candidate_cap: int,
        fts_scores: Mapping[int, float],
    ) -> tuple[list[Mapping[str, Any]], int]:
        base = [
            agent_memories.c.user_id == user_id,
            agent_memories.c.status.in_(statuses),
        ]
        if kind:
            base.append(agent_memories.c.kind == kind)

        exact_conditions = []
        if raw_tokens:
            lowered_tokens = [token.casefold() for token in raw_tokens]
            exact_conditions.extend(
                (
                    func.lower(agent_memories.c.memory_key).in_(lowered_tokens),
                    func.lower(agent_memories.c.category).in_(lowered_tokens),
                )
            )
            numeric_tokens = [token for token in raw_tokens if token.isdigit()]
            if numeric_tokens:
                exact_conditions.append(agent_memories.c.related_entity_id.in_(numeric_tokens))

        escaped_patterns: list[str] = []
        for value in dict.fromkeys([normalized_query, *terms]):
            if not value:
                continue
            escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            escaped_patterns.append(f"%{escaped}%")
        text_conditions = [
            or_(
                func.lower(agent_memories.c.value_json).like(pattern, escape="\\"),
                func.lower(agent_memories.c.memory_key).like(pattern, escape="\\"),
                func.lower(agent_memories.c.category).like(pattern, escape="\\"),
            )
            for pattern in escaped_patterns
        ]
        search_conditions = [*exact_conditions, *text_conditions]
        match_ids: list[int] = []
        fallback_scan_count = 0
        with self.sessions.session() as session:
            if search_conditions:
                fallback_scan_count = 1
                priority = case(
                    *[(condition, index) for index, condition in enumerate(search_conditions)],
                    else_=len(search_conditions),
                )
                match_ids = list(
                    session.execute(
                        select(agent_memories.c.id)
                        .where(*base, or_(*search_conditions))
                        .order_by(
                            priority,
                            agent_memories.c.updated_at.desc(),
                            agent_memories.c.id.desc(),
                        )
                        .limit(candidate_cap)
                    ).scalars()
                )
            recent_ids = list(
                session.execute(
                    select(agent_memories.c.id)
                    .where(*base)
                    .order_by(
                        agent_memories.c.updated_at.desc(),
                        agent_memories.c.id.desc(),
                    )
                    .limit(max(8, min(candidate_cap // 10, 24)))
                ).scalars()
            )
            candidate_ids = list(dict.fromkeys([*fts_scores.keys(), *match_ids, *recent_ids]))[
                :candidate_cap
            ]
            if not candidate_ids:
                return [], fallback_scan_count
            rows = list(
                session.execute(
                    select(agent_memories).where(*base, agent_memories.c.id.in_(candidate_ids))
                ).mappings()
            )
        return rows, fallback_scan_count

    def delete_memory(self, user_id: int, memory_id: int) -> bool:
        with self.sessions.session() as session:
            result = session.execute(
                delete(agent_memories).where(
                    agent_memories.c.id == memory_id,
                    agent_memories.c.user_id == user_id,
                )
            )
            return result.rowcount > 0

    def create_task(self, values: Mapping[str, Any]) -> None:
        with self.sessions.session() as session:
            session.execute(
                update(agent_tasks)
                .where(
                    agent_tasks.c.conversation_id == values["conversation_id"],
                    agent_tasks.c.user_id == values["user_id"],
                    agent_tasks.c.status == "waiting_input",
                )
                .values(status="superseded", updated_at=values["updated_at"])
            )
            session.execute(insert(agent_tasks).values(**values))

    def get_active_task(self, conversation_id: str, user_id: int) -> Mapping[str, Any] | None:
        with self.sessions.session() as session:
            return (
                session.execute(
                    select(agent_tasks)
                    .where(
                        agent_tasks.c.conversation_id == conversation_id,
                        agent_tasks.c.user_id == user_id,
                        agent_tasks.c.status == "waiting_input",
                    )
                    .order_by(agent_tasks.c.updated_at.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )

    def update_task(
        self,
        task_id: str,
        user_id: int,
        *,
        status: str,
        slots_json: str | None,
        result_summary: str,
        updated_at: str,
    ) -> bool:
        values: dict[str, Any] = {
            "status": status,
            "result_summary": result_summary,
            "updated_at": updated_at,
        }
        if slots_json is not None:
            values["slots_json"] = slots_json
        with self.sessions.session() as session:
            result = session.execute(
                update(agent_tasks)
                .where(agent_tasks.c.id == task_id, agent_tasks.c.user_id == user_id)
                .values(**values)
            )
            return result.rowcount > 0

    def record_run(self, values: Mapping[str, Any]) -> None:
        with self.sessions.session() as session:
            session.execute(insert(agent_runs).values(**values))

    def run_count(self, conversation_id: str, user_id: int) -> int:
        with self.sessions.session() as session:
            return int(
                session.execute(
                    select(func.count())
                    .select_from(agent_runs)
                    .where(
                        agent_runs.c.conversation_id == conversation_id,
                        agent_runs.c.user_id == user_id,
                    )
                ).scalar_one()
            )

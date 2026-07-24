from sqlalchemy import Column, Float, ForeignKey, Index, Integer, Table, Text, text

from .base import metadata

agent_conversations = Table(
    "agent_conversations",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("title", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'active'")),
    Column("summary", Text, nullable=False, server_default=text("''")),
    Column("summary_until_message_id", Integer),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

agent_messages = Table(
    "agent_messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("conversation_id", ForeignKey("agent_conversations.id"), nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("role", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata_json", Text, nullable=False, server_default=text("'{}'")),
    Column("created_at", Text, nullable=False),
)

agent_tasks = Table(
    "agent_tasks",
    metadata,
    Column("id", Text, primary_key=True),
    Column("conversation_id", Text, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("task_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("slots_json", Text, nullable=False, server_default=text("'{}'")),
    Column("result_summary", Text, nullable=False, server_default=text("''")),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

agent_memories = Table(
    "agent_memories",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("kind", Text, nullable=False),
    Column("category", Text, nullable=False, server_default=text("''")),
    Column("memory_key", Text, nullable=False, server_default=text("''")),
    Column("value_json", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("status", Text, nullable=False),
    Column("source_message_id", Integer),
    Column("related_entity_type", Text),
    Column("related_entity_id", Text),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

agent_runs = Table(
    "agent_runs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("conversation_id", Text, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("task_id", Text),
    Column("status", Text, nullable=False),
    Column("provider", Text),
    Column("model", Text),
    Column("iterations", Integer, nullable=False, server_default=text("0")),
    Column("tools_json", Text, nullable=False, server_default=text("'[]'")),
    Column("events_json", Text, nullable=False, server_default=text("'[]'")),
    Column("error_code", Text),
    Column("latency_ms", Integer),
    Column("created_at", Text, nullable=False),
)

Index(
    "idx_agent_conversations_user",
    agent_conversations.c.user_id,
    agent_conversations.c.updated_at.desc(),
)
Index(
    "idx_agent_messages_conversation",
    agent_messages.c.conversation_id,
    agent_messages.c.user_id,
    agent_messages.c.id,
)
Index(
    "idx_agent_tasks_conversation",
    agent_tasks.c.conversation_id,
    agent_tasks.c.user_id,
    agent_tasks.c.updated_at.desc(),
)
Index(
    "idx_agent_memories_user",
    agent_memories.c.user_id,
    agent_memories.c.kind,
    agent_memories.c.status,
    agent_memories.c.updated_at.desc(),
)
Index(
    "idx_agent_runs_conversation",
    agent_runs.c.conversation_id,
    agent_runs.c.user_id,
    agent_runs.c.created_at.desc(),
)

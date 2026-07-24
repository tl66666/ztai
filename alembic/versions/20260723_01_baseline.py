"""Establish the SQLAlchemy persistence baseline.

Revision ID: 20260723_01
Revises:
Create Date: 2026-07-23
"""
from __future__ import annotations

from sqlalchemy import Column, inspect, text

from alembic import op
from backend.adapters.persistence.sqlalchemy import metadata

revision = "20260723_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    metadata.create_all(connection, checkfirst=True)
    _repair_legacy_columns(connection)
    for table in metadata.sorted_tables:
        for index in table.indexes:
            index.create(connection, checkfirst=True)
    if connection.dialect.name == "sqlite":
        op.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS agent_memories_fts USING fts5(
                searchable, user_id UNINDEXED, memory_id UNINDEXED
            )
            """
        )
        op.execute("PRAGMA user_version = 5")


def downgrade() -> None:
    # This baseline can adopt an existing local database. Destructive downgrade is
    # deliberately disabled so a migration command cannot erase user career data.
    pass


def _repair_legacy_columns(connection) -> None:
    """Adopt pre-Alembic SQLite databases without running a second migrator."""
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    for table in metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        for model_column in table.columns:
            if model_column.name in existing_columns or model_column.primary_key:
                continue
            default = (
                text(str(model_column.server_default.arg))
                if model_column.server_default is not None
                else None
            )
            op.add_column(
                table.name,
                Column(
                    model_column.name,
                    model_column.type,
                    nullable=True,
                    server_default=default,
                ),
            )

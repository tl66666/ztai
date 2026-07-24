"""Add the independent durable background job queue.

Revision ID: 20260724_02
Revises: 20260723_01
Create Date: 2026-07-24
"""
from __future__ import annotations

from alembic import op
from backend.adapters.jobs.models import background_jobs

revision = "20260724_02"
down_revision = "20260723_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    background_jobs.create(connection, checkfirst=True)
    for index in background_jobs.indexes:
        index.create(connection, checkfirst=True)


def downgrade() -> None:
    background_jobs.drop(op.get_bind(), checkfirst=True)

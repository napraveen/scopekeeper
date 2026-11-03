"""Initial schema with all 11 ScopeKeeper tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables."""
    op.create_table(
        "asks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("source_room", sa.String(128), nullable=False),
        sa.Column("source_message_id", sa.String(128), nullable=False),
        sa.Column("source_link", sa.Text(), nullable=False),
        sa.Column("requester", sa.String(128), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("clause_ids", sa.JSON(), nullable=False),
        sa.Column("related_item", sa.String(32), nullable=True),
        sa.Column("decision_id", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("cr_id", sa.String(32), nullable=True),
        sa.Column("question_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("decided_at", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ask_id", sa.String(32), nullable=False, index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("choices", sa.JSON(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_link", sa.Text(), nullable=True),
        sa.Column("asked_at", sa.String(64), nullable=False),
        sa.Column("answered_at", sa.String(64), nullable=True),
    )
    op.create_table(
        "change_requests",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ask_id", sa.String(32), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("room_id", sa.String(128), nullable=False),
        sa.Column("room_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("estimate", sa.JSON(), nullable=True),
        sa.Column("confirmed_hours", sa.Integer(), nullable=True),
        sa.Column("smaller_confirmed_hours", sa.Integer(), nullable=True),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("envelope_result", sa.JSON(), nullable=True),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("approved_at", sa.String(64), nullable=True),
        sa.Column("approved_options", sa.JSON(), nullable=True),
        sa.Column("client_choice", sa.String(32), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("decided_at", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("date", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
    )
    op.create_table(
        "work_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ask_id", sa.String(32), nullable=False, index=True),
        sa.Column("cr_id", sa.String(32), nullable=True, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("ticket_url", sa.Text(), nullable=False),
        sa.Column("branch", sa.String(256), nullable=False),
        sa.Column("pr_url", sa.Text(), nullable=True),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "goodwill",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("ask_id", sa.String(32), nullable=False, index=True),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.String(128), nullable=False),
        sa.Column("month", sa.String(16), nullable=False, index=True),
        sa.Column("date", sa.String(32), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
    )
    op.create_table(
        "swaps",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("cr_id", sa.String(32), nullable=False, index=True),
        sa.Column("added_title", sa.Text(), nullable=False),
        sa.Column("removed_item_ids", sa.JSON(), nullable=False),
        sa.Column("hours_added", sa.Integer(), nullable=False),
        sa.Column("hours_removed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(64), nullable=False),
    )
    op.create_table(
        "role_shifts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("from_holder", sa.String(128), nullable=False),
        sa.Column("to_holder", sa.String(128), nullable=False),
        sa.Column("at", sa.String(64), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.String(64), nullable=False),
        sa.Column("type", sa.String(64), nullable=False, index=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ask_id", sa.String(32), nullable=True, index=True),
        sa.Column("cr_id", sa.String(32), nullable=True, index=True),
        sa.Column("room_id", sa.String(128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("message_link", sa.Text(), nullable=True),
    )
    op.create_table(
        "processed_events",
        sa.Column("switch_event_id", sa.String(128), primary_key=True),
        sa.Column("processed_at", sa.String(64), nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    """Drop all tables."""
    for name in [
        "settings",
        "processed_events",
        "events",
        "role_shifts",
        "swaps",
        "goodwill",
        "work_items",
        "decisions",
        "change_requests",
        "questions",
        "asks",
    ]:
        op.drop_table(name)

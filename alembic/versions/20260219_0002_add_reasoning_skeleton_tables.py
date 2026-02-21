"""add reasoning skeleton tables

Revision ID: 20260219_0002
Revises: 20260218_0001
Create Date: 2026-02-19 12:10:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260219_0002"
down_revision = "20260218_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names())


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in set(inspector.get_table_names()):
        return False
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("reasoning_session"):
        op.create_table(
            "reasoning_session",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
        )
    if not _index_exists("reasoning_session", "ix_reasoning_session_tenant_id"):
        op.create_index("ix_reasoning_session_tenant_id", "reasoning_session", ["tenant_id"])

    if not _table_exists("reasoning_turn"):
        op.create_table(
            "reasoning_turn",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("reasoning_session.id"), nullable=False),
            sa.Column("turn_no", sa.Integer(), nullable=False),
            sa.Column("user_input", sa.Text(), nullable=False),
            sa.Column("model_output", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("session_id", "turn_no", name="uk_reasoning_turn_session_no"),
        )
    if not _index_exists("reasoning_turn", "ix_reasoning_turn_session_id"):
        op.create_index("ix_reasoning_turn_session_id", "reasoning_turn", ["session_id"])

    if not _table_exists("reasoning_task"):
        op.create_table(
            "reasoning_task",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("reasoning_session.id"), nullable=False),
            sa.Column("turn_id", sa.Integer(), sa.ForeignKey("reasoning_turn.id"), nullable=False),
            sa.Column("task_type", sa.String(length=64), nullable=False),
            sa.Column("task_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not _index_exists("reasoning_task", "ix_reasoning_task_session_id"):
        op.create_index("ix_reasoning_task_session_id", "reasoning_task", ["session_id"])
    if not _index_exists("reasoning_task", "ix_reasoning_task_turn_id"):
        op.create_index("ix_reasoning_task_turn_id", "reasoning_task", ["turn_id"])
    if not _index_exists("reasoning_task", "ix_reasoning_task_status"):
        op.create_index("ix_reasoning_task_status", "reasoning_task", ["status"])

    if not _table_exists("reasoning_context"):
        op.create_table(
            "reasoning_context",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("reasoning_session.id"), nullable=False),
            sa.Column("scope", sa.String(length=16), nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if not _index_exists("reasoning_context", "ix_reasoning_context_session_id"):
        op.create_index("ix_reasoning_context_session_id", "reasoning_context", ["session_id"])
    if not _index_exists("reasoning_context", "ix_reasoning_context_scope"):
        op.create_index("ix_reasoning_context_scope", "reasoning_context", ["scope"])
    if not _index_exists("reasoning_context", "ix_reasoning_context_key"):
        op.create_index("ix_reasoning_context_key", "reasoning_context", ["key"])

    if not _table_exists("reasoning_trace_event"):
        op.create_table(
            "reasoning_trace_event",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("reasoning_session.id"), nullable=False),
            sa.Column("turn_id", sa.Integer(), sa.ForeignKey("reasoning_turn.id"), nullable=True),
            sa.Column("step", sa.String(length=64), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("trace_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if not _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_session_id"):
        op.create_index("ix_reasoning_trace_event_session_id", "reasoning_trace_event", ["session_id"])
    if not _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_turn_id"):
        op.create_index("ix_reasoning_trace_event_turn_id", "reasoning_trace_event", ["turn_id"])
    if not _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_step"):
        op.create_index("ix_reasoning_trace_event_step", "reasoning_trace_event", ["step"])
    if not _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_event_type"):
        op.create_index("ix_reasoning_trace_event_event_type", "reasoning_trace_event", ["event_type"])
    if not _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_trace_id"):
        op.create_index("ix_reasoning_trace_event_trace_id", "reasoning_trace_event", ["trace_id"])

    if not _table_exists("reasoning_clarification"):
        op.create_table(
            "reasoning_clarification",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("reasoning_session.id"), nullable=False),
            sa.Column("turn_id", sa.Integer(), sa.ForeignKey("reasoning_turn.id"), nullable=True),
            sa.Column("question_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("answer_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not _index_exists("reasoning_clarification", "ix_reasoning_clarification_session_id"):
        op.create_index("ix_reasoning_clarification_session_id", "reasoning_clarification", ["session_id"])
    if not _index_exists("reasoning_clarification", "ix_reasoning_clarification_turn_id"):
        op.create_index("ix_reasoning_clarification_turn_id", "reasoning_clarification", ["turn_id"])
    if not _index_exists("reasoning_clarification", "ix_reasoning_clarification_status"):
        op.create_index("ix_reasoning_clarification_status", "reasoning_clarification", ["status"])


def downgrade() -> None:
    if _index_exists("reasoning_clarification", "ix_reasoning_clarification_status"):
        op.drop_index("ix_reasoning_clarification_status", table_name="reasoning_clarification")
    if _index_exists("reasoning_clarification", "ix_reasoning_clarification_turn_id"):
        op.drop_index("ix_reasoning_clarification_turn_id", table_name="reasoning_clarification")
    if _index_exists("reasoning_clarification", "ix_reasoning_clarification_session_id"):
        op.drop_index("ix_reasoning_clarification_session_id", table_name="reasoning_clarification")
    if _table_exists("reasoning_clarification"):
        op.drop_table("reasoning_clarification")

    if _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_trace_id"):
        op.drop_index("ix_reasoning_trace_event_trace_id", table_name="reasoning_trace_event")
    if _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_event_type"):
        op.drop_index("ix_reasoning_trace_event_event_type", table_name="reasoning_trace_event")
    if _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_step"):
        op.drop_index("ix_reasoning_trace_event_step", table_name="reasoning_trace_event")
    if _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_turn_id"):
        op.drop_index("ix_reasoning_trace_event_turn_id", table_name="reasoning_trace_event")
    if _index_exists("reasoning_trace_event", "ix_reasoning_trace_event_session_id"):
        op.drop_index("ix_reasoning_trace_event_session_id", table_name="reasoning_trace_event")
    if _table_exists("reasoning_trace_event"):
        op.drop_table("reasoning_trace_event")

    if _index_exists("reasoning_context", "ix_reasoning_context_key"):
        op.drop_index("ix_reasoning_context_key", table_name="reasoning_context")
    if _index_exists("reasoning_context", "ix_reasoning_context_scope"):
        op.drop_index("ix_reasoning_context_scope", table_name="reasoning_context")
    if _index_exists("reasoning_context", "ix_reasoning_context_session_id"):
        op.drop_index("ix_reasoning_context_session_id", table_name="reasoning_context")
    if _table_exists("reasoning_context"):
        op.drop_table("reasoning_context")

    if _index_exists("reasoning_task", "ix_reasoning_task_status"):
        op.drop_index("ix_reasoning_task_status", table_name="reasoning_task")
    if _index_exists("reasoning_task", "ix_reasoning_task_turn_id"):
        op.drop_index("ix_reasoning_task_turn_id", table_name="reasoning_task")
    if _index_exists("reasoning_task", "ix_reasoning_task_session_id"):
        op.drop_index("ix_reasoning_task_session_id", table_name="reasoning_task")
    if _table_exists("reasoning_task"):
        op.drop_table("reasoning_task")

    if _index_exists("reasoning_turn", "ix_reasoning_turn_session_id"):
        op.drop_index("ix_reasoning_turn_session_id", table_name="reasoning_turn")
    if _table_exists("reasoning_turn"):
        op.drop_table("reasoning_turn")

    if _index_exists("reasoning_session", "ix_reasoning_session_tenant_id"):
        op.drop_index("ix_reasoning_session_tenant_id", table_name="reasoning_session")
    if _table_exists("reasoning_session"):
        op.drop_table("reasoning_session")

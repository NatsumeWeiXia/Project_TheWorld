"""add active tenant table

Revision ID: 20260219_0004
Revises: 20260219_0003
Create Date: 2026-02-19 21:10:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260219_0004"
down_revision = "20260219_0003"
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
    if not _table_exists("active_tenant"):
        op.create_table(
            "active_tenant",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uk_active_tenant_tenant"),
        )
    if not _index_exists("active_tenant", "ix_active_tenant_tenant_id"):
        op.create_index("ix_active_tenant_tenant_id", "active_tenant", ["tenant_id"])


def downgrade() -> None:
    if _index_exists("active_tenant", "ix_active_tenant_tenant_id"):
        op.drop_index("ix_active_tenant_tenant_id", table_name="active_tenant")
    if _table_exists("active_tenant"):
        op.drop_table("active_tenant")

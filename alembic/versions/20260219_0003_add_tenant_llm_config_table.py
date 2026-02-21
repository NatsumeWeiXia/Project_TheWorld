"""add tenant llm config table

Revision ID: 20260219_0003
Revises: 20260219_0002
Create Date: 2026-02-19 13:20:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260219_0003"
down_revision = "20260219_0002"
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
    if not _table_exists("tenant_llm_config"):
        op.create_table(
            "tenant_llm_config",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("api_key_cipher", sa.Text(), nullable=False),
            sa.Column("base_url", sa.String(length=512), nullable=True),
            sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
            sa.Column("enable_thinking", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("fallback_provider", sa.String(length=32), nullable=True),
            sa.Column("fallback_model", sa.String(length=128), nullable=True),
            sa.Column("extra_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
            sa.Column("updated_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uk_tenant_llm_config_tenant"),
        )
    if not _index_exists("tenant_llm_config", "ix_tenant_llm_config_tenant_id"):
        op.create_index("ix_tenant_llm_config_tenant_id", "tenant_llm_config", ["tenant_id"])


def downgrade() -> None:
    if _index_exists("tenant_llm_config", "ix_tenant_llm_config_tenant_id"):
        op.drop_index("ix_tenant_llm_config_tenant_id", table_name="tenant_llm_config")
    if _table_exists("tenant_llm_config"):
        op.drop_table("tenant_llm_config")

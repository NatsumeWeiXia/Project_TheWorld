"""M1 baseline schema

Revision ID: 20260218_0001
Revises:
Create Date: 2026-02-18 21:05:00
"""
from __future__ import annotations

from alembic import op

from src.app.infra.db.base import Base
from src.app.infra.db import models as _models  # noqa: F401


# revision identifiers, used by Alembic.
revision = "20260218_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)

"""widen rate_forecasts.model  (VARCHAR(48) -> VARCHAR(80))

The ensemble label ``"HoltWinters(damped) + SeasonalNaiveDrift ensemble"`` is
49 characters; SQLite ignores the length cap so tests passed, but the first
real Postgres write raised ``StringDataRightTruncation``.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgres(bind) -> bool:
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    bind = op.get_bind()
    if _is_postgres(bind):  # SQLite has no real VARCHAR length to alter
        op.alter_column(
            "rate_forecasts", "model",
            existing_type=sa.String(48), type_=sa.String(80),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _is_postgres(bind):
        op.alter_column(
            "rate_forecasts", "model",
            existing_type=sa.String(80), type_=sa.String(48),
            existing_nullable=True,
        )

"""phase 2: feed_snapshots, freight_rates, rate_forecasts, alerts

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.db.models import (
    Alert,
    Base,
    FeedSnapshot,
    FreightRate,
    RateForecast,
)

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = [
    FeedSnapshot.__table__, FreightRate.__table__,
    RateForecast.__table__, Alert.__table__,
]


def upgrade() -> None:
    # checkfirst=True -> only the four new Phase 2 tables are created
    Base.metadata.create_all(bind=op.get_bind(), tables=_NEW, checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=_NEW)

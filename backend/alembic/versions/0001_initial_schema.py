"""initial schema: ports, lane_geometry, ingest_runs, vessels, positions, voyages

Revision ID: 0001
Revises:
Create Date: 2026-09-03
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.db.models import Base

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

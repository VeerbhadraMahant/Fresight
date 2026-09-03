"""phase 3: live-monitoring columns on vessels / voyages

Migration 0001 already created ``vessels`` / ``positions`` / ``voyages`` as
stubs. Phase 3 fills them in and needs a few extra nullable columns:

  vessels.nav_status    last reported AIS navigational status
  vessels.destination   free-text AIS destination
  vessels.eta_raw       AIS ETA as reported
  voyages.dest_raw      unresolved AIS destination text

Idempotent: on a fresh DB the tables are created from the current models (which
already declare the columns), so the ``add_column`` calls are skipped.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-03
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.models import Base, Position, Vessel, Voyage

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column-name, type factory)
_ADDED: list[tuple[str, str]] = [
    ("vessels", "nav_status"),
    ("vessels", "destination"),
    ("vessels", "eta_raw"),
    ("voyages", "dest_raw"),
]
_TYPES = {
    "nav_status": sa.String(32),
    "destination": sa.String(120),
    "eta_raw": sa.String(32),
    "dest_raw": sa.String(120),
}


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    # fresh DB: create the three tables straight from the models (columns included)
    Base.metadata.create_all(
        bind=bind,
        tables=[Vessel.__table__, Position.__table__, Voyage.__table__],
        checkfirst=True,
    )
    for table, name in _ADDED:
        if name not in _columns(bind, table):
            op.add_column(table, sa.Column(name, _TYPES[name], nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    for table, name in reversed(_ADDED):
        if name in _columns(bind, table):
            op.drop_column(table, name)

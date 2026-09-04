"""phase D: shipments + shipment_costs

The bridge tables between the analysis engine and the live map. One
``shipments`` row per tracked cargo booking; ``shipment_costs`` accrues one
delivered-cost valuation per ingest run (the "cost in real time" series).

Idempotent: a fresh DB gets both tables straight from the models; an existing
DB (already at 0004, with live vessel data) just gains the two new tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.db.models import Base, Shipment, ShipmentCost

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Shipment.__table__, ShipmentCost.__table__],
        checkfirst=True,
    )


def downgrade() -> None:
    op.drop_table("shipment_costs")
    op.drop_table("shipments")

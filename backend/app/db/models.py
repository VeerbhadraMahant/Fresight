"""SQLAlchemy ORM models -- the persistent, self-updating state.

Phase 1 uses ``ports``, ``lane_geometry`` and ``ingest_runs``. ``vessels``,
``positions`` and ``voyages`` are defined now so the initial migration is
complete; the live-monitoring pipeline (Phase 3) fills them.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    wpi_number: Mapped[int | None] = mapped_column(Integer, index=True)
    unlocode: Mapped[str | None] = mapped_column(String(8), index=True)

    name: Mapped[str] = mapped_column(String(160), index=True)
    name_norm: Mapped[str] = mapped_column(String(160), index=True)
    country: Mapped[str | None] = mapped_column(String(2))
    country_name: Mapped[str | None] = mapped_column(String(80))
    water_body: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(40))     # legacy Region (curated ports)
    basin: Mapped[str | None] = mapped_column(String(40), index=True)  # routing basin
    role: Mapped[str] = mapped_column(String(12), default="both")  # load|discharge|both

    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    max_draft_m: Mapped[float | None] = mapped_column(Float)
    max_loa_m: Mapped[float | None] = mapped_column(Float)
    max_beam_m: Mapped[float | None] = mapped_column(Float)
    max_dwt: Mapped[int | None] = mapped_column(Integer)
    berth_handling_tph: Mapped[float | None] = mapped_column(Float)
    congestion_base_days: Mapped[float | None] = mapped_column(Float)
    harbor_size: Mapped[str | None] = mapped_column(String(16))

    transload: Mapped[bool] = mapped_column(Boolean, default=False)
    curated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(160))

    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_ports_lat_lon", "lat", "lon"),)


class LaneGeometry(Base):
    """Cached sea-route between two ports: land-avoiding distance + polyline."""

    __tablename__ = "lane_geometry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin_code: Mapped[str] = mapped_column(String(24), index=True)
    dest_code: Mapped[str] = mapped_column(String(24), index=True)
    distance_nm: Mapped[float] = mapped_column(Float)
    via: Mapped[list] = mapped_column(JSON, default=list)          # waypoint names
    geometry: Mapped[list] = mapped_column(JSON, default=list)     # [[lon,lat], ...]
    method: Mapped[str] = mapped_column(String(32), default="waypoint-graph-v1")
    created_at: Mapped[datetime] = _now()

    __table_args__ = (UniqueConstraint("origin_code", "dest_code", name="uq_lane_pair"),)


class IngestRun(Base):
    """One execution of a feed ingest -- powers the 'self-updating' status panel."""

    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = _now()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    rows: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- #
# Defined now, populated by the Phase 3 live-monitoring pipeline.
# --------------------------------------------------------------------------- #
class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mmsi: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    imo: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    vessel_type: Mapped[str | None] = mapped_column(String(32))   # inferred bulk class
    dwt: Mapped[int | None] = mapped_column(Integer)
    loa_m: Mapped[float | None] = mapped_column(Float)
    beam_m: Mapped[float | None] = mapped_column(Float)
    draft_m: Mapped[float | None] = mapped_column(Float)
    flag: Mapped[str | None] = mapped_column(String(2))
    last_static_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mmsi: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.mmsi"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    sog_kn: Mapped[float | None] = mapped_column(Float)
    cog_deg: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    nav_status: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(12), default="ais")  # ais|estimated

    __table_args__ = (Index("ix_positions_mmsi_ts", "mmsi", "ts"),)


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mmsi: Mapped[int] = mapped_column(Integer, index=True)
    origin_code: Mapped[str | None] = mapped_column(String(24))
    dest_code: Mapped[str | None] = mapped_column(String(24))
    departure_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eta_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    laden: Mapped[bool | None] = mapped_column(Boolean)
    cargo_guess: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


ALL_TABLES = [
    Port.__table__, LaneGeometry.__table__, IngestRun.__table__,
    Vessel.__table__, Position.__table__, Voyage.__table__,
]

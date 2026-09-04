"""Phase 3 -- turn an AIS sample into persistent ``vessels`` / ``positions`` /
``voyages`` state, then fill AIS gaps with dead-reckoning.

Called once per ingest run from ``worker/ingest.py`` (best-effort: any failure is
logged and the rest of the run proceeds). With no ``AISSTREAM_API_KEY`` the whole
step is a no-op.

Pipeline:
  1. upsert ``vessels`` from static frames (name / type / dims / destination);
  2. append de-duplicated observed ``positions`` (source='ais');
  3. re-project each fleet member forward from its last AIS fix -> one rolling
     ``positions`` row per vessel (source='estimated');
  4. infer coarse ``voyages`` from "at a berth" vs "at sea" transitions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from app.db import session_scope
from app.db.models import Position, Vessel, Voyage
from app.geo import ports as port_reg
from app.live.ais import is_dry_bulk, sample
from app.live.reckon import dead_reckon, nearest_port

log = logging.getLogger("freightsight.worker.live")

PORT_CALL_NM = 12.0       # within this of a port + slow -> "at a berth / roads"
PORT_CALL_SOG = 1.0
RECKON_AFTER_MIN = 35.0   # start dead-reckoning once the last AIS fix is this old
RECKON_MAX_HOURS = 36.0   # ... but give up after this (position too uncertain)
TRACK_PRUNE_DAYS = 10     # drop observed points older than this each run


def _naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
def _persist_statics(statics: list) -> int:
    if not statics:
        return 0
    now = _now()
    n = 0
    with session_scope() as s:
        for st in statics:
            v = s.scalars(select(Vessel).where(Vessel.mmsi == st.mmsi)).first()
            if v is None:
                v = Vessel(mmsi=st.mmsi)
                s.add(v)
            v.name = st.name or v.name
            v.imo = st.imo or v.imo
            v.loa_m = st.loa_m or v.loa_m
            v.beam_m = st.beam_m or v.beam_m
            v.draft_m = st.draft_m or v.draft_m
            v.destination = st.destination or v.destination
            v.eta_raw = st.eta_raw or v.eta_raw
            if st.ship_type is not None:
                v.vessel_type = "dry_bulk" if is_dry_bulk(st.ship_type) else f"type_{st.ship_type}"
            v.last_static_at = now
            n += 1
    return n


def _ensure_vessels(mmsis: set[int]) -> None:
    if not mmsis:
        return
    with session_scope() as s:
        have = set(s.scalars(select(Vessel.mmsi).where(Vessel.mmsi.in_(mmsis))).all())
        for m in mmsis - have:
            s.add(Vessel(mmsi=m))


def _persist_positions(positions: list) -> int:
    if not positions:
        return 0
    _ensure_vessels({p.mmsi for p in positions})
    written = 0
    with session_scope() as s:
        for p in positions:
            ts = _naive_utc(p.ts)
            exists = s.scalar(
                select(func.count())
                .select_from(Position)
                .where(Position.mmsi == p.mmsi, Position.ts == ts, Position.source == "ais")
            )
            if exists:
                continue
            s.add(Position(
                mmsi=p.mmsi, ts=ts, lat=p.lat, lon=p.lon,
                sog_kn=p.sog_kn, cog_deg=p.cog_deg, heading_deg=p.heading_deg,
                nav_status=p.nav_status, source="ais",
            ))
            written += 1
        # keep the observed track bounded
        cutoff = _now() - timedelta(days=TRACK_PRUNE_DAYS)
        s.execute(delete(Position).where(Position.source == "ais", Position.ts < cutoff))
    # mirror last nav status onto the vessel row
    with session_scope() as s:
        for p in positions:
            if p.nav_status:
                v = s.scalars(select(Vessel).where(Vessel.mmsi == p.mmsi)).first()
                if v:
                    v.nav_status = p.nav_status
    return written


def _latest_ais_per_vessel(s) -> list:
    sub = (
        select(Position.mmsi, func.max(Position.ts).label("mts"))
        .where(Position.source == "ais")
        .group_by(Position.mmsi)
        .subquery()
    )
    return s.execute(
        select(Position.mmsi, Position.lat, Position.lon, Position.sog_kn,
               Position.cog_deg, Position.ts)
        .join(sub, (Position.mmsi == sub.c.mmsi) & (Position.ts == sub.c.mts))
        .where(Position.source == "ais")
    ).all()


def _dead_reckon_stale() -> int:
    now = _now()
    n = 0
    with session_scope() as s:
        rows = _latest_ais_per_vessel(s)
        for mmsi, lat, lon, sog, cog, ts in rows:
            # Postgres ``timestamptz`` reads back tz-aware; ``now`` is naive-UTC
            # (SQLite hands back naive, so tests never caught the mismatch).
            age_min = (now - _naive_utc(ts)).total_seconds() / 60.0
            if age_min < RECKON_AFTER_MIN or age_min > RECKON_MAX_HOURS * 60:
                continue
            if not sog or sog < 0.5 or cog is None:
                continue
            nlat, nlon = dead_reckon(lat, lon, sog, cog, age_min)
            s.execute(delete(Position).where(
                Position.mmsi == mmsi, Position.source == "estimated"
            ))
            s.add(Position(
                mmsi=mmsi, ts=now, lat=nlat, lon=nlon, sog_kn=sog, cog_deg=cog,
                nav_status="dead-reckoned", source="estimated",
            ))
            n += 1
    return n


def _resolve_dest(raw: str | None) -> str | None:
    if not raw:
        return None
    p = port_reg.get(raw) or port_reg.get(raw.split(">")[-1].strip())
    return p.code if p else None


def _infer_voyages() -> dict:
    now = _now()
    opened = closed = 0
    with session_scope() as s:
        rows = _latest_ais_per_vessel(s)
        for mmsi, lat, lon, sog, _cog, _ts in rows:
            port, _d = nearest_port(lat, lon, max_nm=PORT_CALL_NM)
            in_port = port is not None and (sog or 0.0) <= PORT_CALL_SOG
            cur = s.scalars(
                select(Voyage).where(Voyage.mmsi == mmsi).order_by(Voyage.id.desc())
            ).first()
            vessel = s.scalars(select(Vessel).where(Vessel.mmsi == mmsi)).first()
            dest_raw = vessel.destination if vessel else None

            if in_port:
                if cur is None or cur.status == "completed":
                    s.add(Voyage(mmsi=mmsi, origin_code=port.code, status="in_port",
                                 updated_at=now))
                elif cur.status == "active":
                    cur.dest_code = port.code
                    cur.eta_ts = now
                    cur.status = "completed"
                    cur.confidence = 0.45
                    closed += 1
                    s.add(Voyage(mmsi=mmsi, origin_code=port.code, status="in_port",
                                 updated_at=now))
                else:  # already in_port -> refine which port
                    cur.origin_code = port.code
            else:  # at sea
                if cur is None or cur.status == "completed":
                    s.add(Voyage(mmsi=mmsi, status="active", departure_ts=now,
                                 dest_raw=dest_raw, dest_code=_resolve_dest(dest_raw),
                                 confidence=0.3, updated_at=now))
                    opened += 1
                elif cur.status == "in_port":
                    cur.status = "active"
                    cur.departure_ts = now
                    cur.dest_raw = dest_raw
                    cur.dest_code = _resolve_dest(dest_raw)
                    cur.confidence = 0.3
                    opened += 1
                elif dest_raw and not cur.dest_raw:
                    cur.dest_raw = dest_raw
                    cur.dest_code = _resolve_dest(dest_raw)
    return {"voyages_opened": opened, "voyages_closed": closed}


# --------------------------------------------------------------------------- #
def run_live() -> dict:
    """One AIS pass. Returns a summary dict; never raises."""
    s = sample()
    if not s["ok"]:
        log.warning("AIS step skipped: %s", s["reason"])
        return {"skipped": s["reason"], "ais_positions": 0}

    statics = _persist_statics(s["statics"])
    observed = _persist_positions(s["positions"])
    reckoned = _dead_reckon_stale()
    voyages = _infer_voyages()
    out = {
        "ais_positions": observed,
        "statics": statics,
        "reckoned": reckoned,
        "seen_mmsi": len({p.mmsi for p in s["positions"]}),
        **voyages,
    }
    log.info("AIS step: %s", out)
    return out

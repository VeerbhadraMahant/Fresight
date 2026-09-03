"""Live-map read endpoints (Phase 3).

  GET /api/map/summary          tracked-vessel / voyage counts + last AIS sample
  GET /api/map/vessels          latest fix per vessel (observed + dead-reckoned)
  GET /api/map/vessel/{mmsi}    one vessel: static, recent track, current voyage
  GET /api/map/ports            port markers  (works with NO database -- registry)

Ports + sea lanes render with zero configuration. Vessel layers populate once
``DATABASE_URL`` is set and the ingest worker has run at least once; endpoints
return ``{"enabled": false, ...}`` until then.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from ..db import DB_ENABLED
from ..geo import ports as port_reg

router = APIRouter(prefix="/api/map", tags=["map"])


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    """"minLon,minLat,maxLon,maxLat" -> tuple, or None."""
    if not bbox:
        return None
    try:
        a, b, c, d = (float(x) for x in bbox.split(","))
    except (ValueError, TypeError):
        raise HTTPException(400, "bbox must be 'minLon,minLat,maxLon,maxLat'") from None
    return min(a, c), min(b, d), max(a, c), max(b, d)


def _in_bbox(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


# --------------------------------------------------------------------------- #
@router.get("/ports")
def map_ports(
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    curated_only: bool = False,
    limit: int = Query(1500, ge=1, le=8000),
):
    box = _parse_bbox(bbox)
    out = []
    for p in port_reg.REGISTRY.all():
        if curated_only and not p.curated:
            continue
        if box and not _in_bbox(p.lon, p.lat, box):
            continue
        out.append({
            "code": p.code, "name": p.name, "lat": round(p.lat, 4), "lon": round(p.lon, 4),
            "basin": p.basin, "country": p.country, "curated": p.curated,
        })
        if len(out) >= limit:
            break
    return {"enabled": True, "backend": port_reg.REGISTRY.backend,
            "count": len(out), "ports": out}


@router.get("/summary")
def map_summary():
    base = {"enabled": DB_ENABLED, "ports": port_reg.REGISTRY.count()}
    if not DB_ENABLED:
        return {**base, "vessels": 0, "observed": 0, "estimated": 0,
                "active_voyages": 0, "last_sample_at": None}
    from sqlalchemy import func, select

    from ..db import session_scope
    from ..db.models import IngestRun, Position, Voyage

    with session_scope() as s:
        vessels = s.scalar(select(func.count(func.distinct(Position.mmsi)))) or 0
        observed = s.scalar(
            select(func.count()).select_from(Position).where(Position.source == "ais")
        ) or 0
        estimated = s.scalar(
            select(func.count()).select_from(Position).where(Position.source == "estimated")
        ) or 0
        active = s.scalar(
            select(func.count()).select_from(Voyage).where(Voyage.status.in_(("active", "in_port")))
        ) or 0
        last = s.scalar(
            select(func.max(IngestRun.finished_at)).where(
                IngestRun.feed == "ais", IngestRun.ok.is_(True)
            )
        )
    return {**base, "vessels": vessels, "observed": observed, "estimated": estimated,
            "active_voyages": active,
            "last_sample_at": last.isoformat() if last else None}


@router.get("/vessels")
def map_vessels(
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    max_age_h: float = Query(48.0, gt=0, le=240),
    include_estimated: bool = True,
    limit: int = Query(1000, ge=1, le=4000),
):
    if not DB_ENABLED:
        return {"enabled": False, "generated_at": None, "vessels": []}
    from sqlalchemy import and_, func, select

    from ..db import session_scope
    from ..db.models import Position, Vessel

    box = _parse_bbox(bbox)
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=max_age_h)
    sources = ("ais", "estimated") if include_estimated else ("ais",)

    with session_scope() as s:
        sub = (
            select(Position.mmsi, func.max(Position.ts).label("mts"))
            .where(Position.source.in_(sources), Position.ts >= cutoff)
            .group_by(Position.mmsi)
            .subquery()
        )
        rows = s.execute(
            select(Position, Vessel)
            .join(sub, and_(Position.mmsi == sub.c.mmsi, Position.ts == sub.c.mts))
            .join(Vessel, Vessel.mmsi == Position.mmsi, isouter=True)
            .limit(limit * 3)
        ).all()

    vessels = []
    for pos, v in rows:
        if box and not _in_bbox(pos.lon, pos.lat, box):
            continue
        vessels.append({
            "mmsi": pos.mmsi,
            "name": (v.name if v else None),
            "type": (v.vessel_type if v else None),
            "lat": round(pos.lat, 5), "lon": round(pos.lon, 5),
            "sog_kn": pos.sog_kn, "cog_deg": pos.cog_deg,
            "heading_deg": pos.heading_deg,
            "nav_status": pos.nav_status or (v.nav_status if v else None),
            "source": pos.source,
            "ts": pos.ts.isoformat() if pos.ts else None,
            "destination": (v.destination if v else None),
        })
        if len(vessels) >= limit:
            break
    return {"enabled": True,
            "generated_at": datetime.now(UTC).isoformat(),
            "count": len(vessels), "vessels": vessels}


@router.get("/vessel/{mmsi}")
def map_vessel(mmsi: int, track_h: float = Query(72.0, gt=0, le=480)):
    if not DB_ENABLED:
        return {"enabled": False, "mmsi": mmsi}
    from sqlalchemy import select

    from ..db import session_scope
    from ..db.models import Position, Vessel, Voyage

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=track_h)
    with session_scope() as s:
        v = s.scalars(select(Vessel).where(Vessel.mmsi == mmsi)).first()
        pts = s.scalars(
            select(Position)
            .where(Position.mmsi == mmsi, Position.ts >= cutoff)
            .order_by(Position.ts.asc())
        ).all()
        voyage = s.scalars(
            select(Voyage).where(Voyage.mmsi == mmsi).order_by(Voyage.id.desc())
        ).first()

    if v is None and not pts:
        raise HTTPException(404, f"no tracked vessel with MMSI {mmsi}")

    track = [
        {"lat": round(p.lat, 5), "lon": round(p.lon, 5),
         "ts": p.ts.isoformat() if p.ts else None,
         "sog_kn": p.sog_kn, "source": p.source}
        for p in pts
    ]
    return {
        "enabled": True,
        "vessel": {
            "mmsi": mmsi,
            "name": v.name if v else None,
            "imo": v.imo if v else None,
            "type": v.vessel_type if v else None,
            "loa_m": v.loa_m if v else None,
            "beam_m": v.beam_m if v else None,
            "draft_m": v.draft_m if v else None,
            "destination": v.destination if v else None,
            "eta_raw": v.eta_raw if v else None,
            "nav_status": v.nav_status if v else None,
        },
        "track": track,
        "latest": track[-1] if track else None,
        "voyage": None if voyage is None else {
            "status": voyage.status,
            "origin_code": voyage.origin_code,
            "dest_code": voyage.dest_code,
            "dest_raw": voyage.dest_raw,
            "departure_ts": voyage.departure_ts.isoformat() if voyage.departure_ts else None,
            "eta_ts": voyage.eta_ts.isoformat() if voyage.eta_ts else None,
            "confidence": voyage.confidence,
        },
    }

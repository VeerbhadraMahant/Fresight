"""Global geography endpoints: port search/resolve, sea routes, any-lane economics.

Additive to the curated ``/api/reference/*`` and ``/api/scenario`` endpoints --
those keep their exact behaviour for the East-Coast-India lanes. These extend the
product to *any port to any port* worldwide.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .. import __version__
from ..db import DB_ENABLED, healthcheck
from ..geo import lane as lane_mod
from ..geo import ports as port_reg
from ..geo.searoute import graph_stats, sea_route
from ..market_store import STORE
from ..reference_data import VESSEL_ORDER

router = APIRouter(prefix="/api", tags=["global"])


def _market_inputs() -> tuple[float, dict[str, float]]:
    m = STORE.require()
    bunker = float(m.bunker.iloc[-1])
    tce = {n: float(m.tce[n].iloc[-1]) for n in VESSEL_ORDER if n in m.tce.columns}
    return bunker, tce


@router.get("/reference/ports/search")
def ports_search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    return {"query": q, "results": [p.to_public() for p in port_reg.search(q, limit)]}


@router.get("/reference/port")
def resolve_port(ident: str = Query(..., description="code, UN/LOCODE, WPI number, name or 'lat,lon'")):
    p = port_reg.get(ident)
    if p is None:
        raise HTTPException(404, f"no port matches {ident!r}")
    return p.to_public()


@router.get("/reference/ports/stats")
def ports_stats():
    reg = port_reg.REGISTRY
    ports = reg.all()
    basins: dict[str, int] = {}
    for p in ports:
        basins[p.basin or "UNKNOWN"] = basins.get(p.basin or "UNKNOWN", 0) + 1
    return {
        "count": len(ports),
        "backend": reg.backend,
        "curated": sum(1 for p in ports if p.curated),
        "basins": dict(sorted(basins.items())),
    }


@router.get("/geo/route")
def geo_route(origin: str, destination: str):
    o, d = port_reg.get(origin), port_reg.get(destination)
    if o is None or d is None:
        raise HTTPException(404, "unknown origin or destination port")
    r = sea_route(o.lat, o.lon, d.lat, d.lon, o.basin, d.basin)
    return {
        "origin": o.to_public(), "destination": d.to_public(),
        **r.as_dict(),
    }


@router.get("/geo/lane")
def geo_lane(
    origin: str,
    destination: str,
    commodity: str = "Thermal Coal",
    cargo_volume_t: float = Query(150_000, gt=0),
):
    o, d = port_reg.get(origin), port_reg.get(destination)
    if o is None or d is None:
        raise HTTPException(404, "unknown origin or destination port")
    if o.code == d.code:
        raise HTTPException(400, "origin and destination are the same port")
    bunker, tce = _market_inputs()
    return lane_mod.analyse_lane(
        o, d, bunker_usd_t=bunker, tce_by_vessel=tce,
        commodity=commodity, cargo_volume_t=cargo_volume_t,
    )


@router.get("/system/health", tags=["meta"])
def system_health():
    reg = port_reg.REGISTRY
    prov = STORE.provenance
    return {
        "version": __version__,
        "database": {"configured": DB_ENABLED, **healthcheck()},
        "ports": {"count": reg.count(), "backend": reg.backend},
        "searoute": graph_stats(),
        "market": {
            "mode": prov.mode,
            "snapshot_date": prov.snapshot_date,
            "refreshing": prov.refreshing,
            "data_sources": prov.data_sources,
        },
    }

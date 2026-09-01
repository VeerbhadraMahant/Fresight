"""Reference data + market snapshot endpoints."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from .. import reference_data as ref
from ..market_store import STORE

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/ports")
def ports():
    return {
        "discharge_ports": [ref.port_public_view(ref.PORTS[c]) for c in ref.DISCHARGE_PORTS],
        "load_ports": [ref.port_public_view(ref.PORTS[c]) for c in ref.LOAD_PORTS],
    }


@router.get("/vessels")
def vessels():
    return [ref.vessel_public_view(ref.VESSEL_CLASSES[n]) for n in ref.VESSEL_ORDER]


@router.get("/routes")
def routes():
    return [ref.route_public_view(r) for r in ref.ROUTES.values()]


@router.get("/commodities")
def commodities():
    return [
        {"name": c.name, "stowage_factor_m3_t": c.stowage_factor_m3_t,
         "default_parcel_range_t": list(c.default_parcel_range_t)}
        for c in ref.COMMODITIES.values()
    ]


@router.get("/market/provenance")
def provenance():
    m = STORE.require()
    p = STORE.provenance
    return {
        "mode": p.mode,
        "note": p.note,
        "data_sources": p.data_sources,
        "snapshot_date": p.snapshot_date,
        "refreshing": p.refreshing,
        "weather_ports": sorted(m.weather.keys()),
        "generated_at": p.generated_at,
        "history_start": str(m.freight.index[0].date()),
        "history_end": str(m.freight.index[-1].date()),
        "series_count": m.freight.shape[1],
        "daily_rows": int(m.freight.shape[0]),
    }


@router.get("/market/snapshot")
def snapshot():
    m = STORE.require()
    latest = m.freight.iloc[-1]
    prev = m.freight.iloc[-31]
    rows = []
    for (rid, vessel), val in latest.items():
        if pd.isna(val):
            continue
        p = prev[(rid, vessel)]
        chg = None if pd.isna(p) or p == 0 else round((val / p - 1) * 100, 1)
        rows.append({
            "route_id": rid, "lane": ref.ROUTES[rid].lane, "vessel": vessel,
            "rate_usd_t": round(float(val), 2), "change_30d_pct": chg,
        })
    rows.sort(key=lambda r: (r["route_id"], ref.VESSEL_ORDER.index(r["vessel"])))
    return {
        "as_of": str(m.freight.index[-1].date()),
        "vlsfo_usd_t": round(float(m.bunker.iloc[-1]), 1),
        "vlsfo_change_30d_pct": round(float(m.bunker.iloc[-1] / m.bunker.iloc[-31] - 1) * 100, 1),
        "tce_usd_day": {k: round(float(m.tce[k].iloc[-1])) for k in ref.VESSEL_ORDER},
        "congestion_days": {
            ref.PORTS[c].name: round(float(m.congestion[c].iloc[-7:].mean()), 2)
            for c in ref.DISCHARGE_PORTS
        },
        "rates": rows,
    }


@router.get("/market/series")
def series(route_id: str, vessel: str, weeks: int = 130):
    """Weekly history for one route x vessel (for charts)."""
    m = STORE.require()
    if (route_id, vessel) not in m.freight.columns:
        return {"error": "no series for that route/vessel", "route_id": route_id, "vessel": vessel}
    s = m.freight_series(route_id, vessel).resample("W-MON").mean().dropna().iloc[-weeks:]
    return {
        "route_id": route_id, "vessel": vessel, "lane": ref.ROUTES[route_id].lane,
        "points": [{"date": d.strftime("%Y-%m-%d"), "rate": round(float(v), 2)}
                   for d, v in s.items()],
    }

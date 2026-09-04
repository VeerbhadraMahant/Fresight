"""Shipment tracking -- the bridge between the analysis engine and the live map.

A :class:`~app.db.models.Shipment` is one cargo booking under watch: cargo +
lane + (optionally) the physical vessel carrying it (``assigned_mmsi``). This
module turns that row into a live picture:

  * **delivered cost now** -- ``vessel_optimizer.optimise`` re-run against the
    current market snapshot (live bunker / congestion / weather), for the pinned
    vessel class (or the optimiser's pick);
  * **voyage progress + routed ETA** -- from the assigned vessel's latest AIS /
    dead-reckoned fix, using the same basin-aware sea-route graph the economics
    use;
  * **drift** -- delivered USD/t now vs the baseline captured when the shipment
    was created.

Everything here needs a database (``DATABASE_URL``). The router returns
``{"enabled": false}`` when there is none, exactly like the live-map endpoints.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select

from .db import session_scope
from .db.models import Position, Shipment, ShipmentCost, Vessel
from .geo import ports as port_reg
from .geo.searoute import sea_route
from .market_store import STORE
from .synthetic import MarketData
from .vessel_optimizer import optimise as run_optimise

log = logging.getLogger("freightsight.shipments")

_TERMINAL = {"arrived", "cancelled"}
_DEFAULT_SPEED_KN = 12.5  # laden bulker cruise, when we have no live speed


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(UTC)


def _gen_ref() -> str:
    return "SHP-" + secrets.token_hex(3).upper()


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


def _public(s: Shipment) -> dict:
    return {
        "ref": s.ref,
        "commodity": s.commodity,
        "cargo_t": s.cargo_t,
        "origin_code": s.origin_code,
        "dest_code": s.dest_code,
        "vessel_class": s.vessel_class,
        "assigned_mmsi": s.assigned_mmsi,
        "laycan_start": s.laycan_start.isoformat() if s.laycan_start else None,
        "laycan_end": s.laycan_end.isoformat() if s.laycan_end else None,
        "contract_months": s.contract_months,
        "status": s.status,
        "baseline_usd_per_t": s.baseline_usd_per_t,
        "baseline_at": s.baseline_at.isoformat() if s.baseline_at else None,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _live_vessel(mmsi: int | None) -> dict | None:
    """Latest fix (AIS or dead-reckoned) + static data for the assigned vessel."""
    if not mmsi:
        return None
    with session_scope() as s:
        pos = s.scalars(
            select(Position).where(Position.mmsi == mmsi).order_by(desc(Position.ts))
        ).first()
        v = s.scalars(select(Vessel).where(Vessel.mmsi == mmsi)).first()
    if pos is None and v is None:
        return None
    return {
        "mmsi": mmsi,
        "name": v.name if v else None,
        "type": v.vessel_type if v else None,
        "imo": v.imo if v else None,
        "destination": v.destination if v else None,
        "eta_raw": v.eta_raw if v else None,
        "lat": round(pos.lat, 5) if pos else None,
        "lon": round(pos.lon, 5) if pos else None,
        "sog_kn": pos.sog_kn if pos else None,
        "cog_deg": pos.cog_deg if pos else None,
        "nav_status": (pos.nav_status if pos else None) or (v.nav_status if v else None),
        "source": pos.source if pos else None,
        "ts": pos.ts.isoformat() if pos and pos.ts else None,
    }


def _progress(shipment: Shipment, live: dict | None) -> dict:
    """Voyage completion + routed distance-remaining + ETA from the live fix.

    Uses the basin-aware sea-route graph so 'remaining' bends around the same
    canals/capes the cost model assumes. Returns zeros/None when we have no
    usable position.
    """
    out: dict = {"progress_pct": None, "distance_remaining_nm": None,
                 "distance_total_nm": None, "eta_ts": None, "speed_used_kn": None}
    o = port_reg.get(shipment.origin_code)
    d = port_reg.get(shipment.dest_code)
    if o is None or d is None:
        return out
    total = sea_route(o.lat, o.lon, d.lat, d.lon, o.basin, d.basin).distance_nm
    out["distance_total_nm"] = round(total)
    if not live or live.get("lat") is None:
        return out

    remaining = sea_route(live["lat"], live["lon"], d.lat, d.lon, None, d.basin).distance_nm
    remaining = min(remaining, total)  # never report "further than the whole lane"
    frac = 1.0 - (remaining / total if total > 0 else 1.0)
    out["distance_remaining_nm"] = round(remaining)
    out["progress_pct"] = round(max(0.0, min(1.0, frac)) * 100, 1)

    sog = live.get("sog_kn")
    speed = sog if (sog and sog > 3.0) else _DEFAULT_SPEED_KN
    out["speed_used_kn"] = round(speed, 1)
    if remaining > 1.0:
        hrs = remaining / speed
        out["eta_ts"] = (_now() + timedelta(hours=hrs)).isoformat()
    else:
        out["eta_ts"] = _now().isoformat()
    return out


def _choose_option(opt: dict, vessel_class: str | None) -> dict | None:
    opts = opt.get("options") or []
    if vessel_class:
        for o in opts:
            if o["vessel"] == vessel_class:
                return o
    rec = opt.get("recommendation")
    if rec:
        for o in opts:
            if o["vessel"] == rec["vessel"]:
                return o
    feasible = [o for o in opts if o.get("feasible")]
    return (feasible or opts or [None])[0]


# --------------------------------------------------------------------------- #
# valuation -- the "cost in real time" core
# --------------------------------------------------------------------------- #
def revalue(shipment: Shipment, *, market: MarketData | None = None,
            run_id: int | None = None, persist: bool = False) -> dict:
    """Value the shipment against the current market snapshot + live position.

    Returns a dict with delivered USD/t, drift vs baseline, voyage progress and
    routed ETA. When ``persist`` is set, also appends a ``shipment_costs`` row.
    ``market`` defaults to the API's shared store; the ingest worker passes its
    freshly built dataset.
    """
    m = market or STORE.require()
    laycan_month = shipment.laycan_start.month if shipment.laycan_start else None
    opt = run_optimise(
        m, shipment.origin_code, shipment.dest_code, shipment.commodity,
        float(shipment.cargo_t), laycan_month=laycan_month,
    )
    chosen = _choose_option(opt, shipment.vessel_class)
    if chosen is None:
        raise ValueError("no vessel option could be evaluated for this lane")

    delivered = float(chosen["delivered_cost_usd_per_t"])
    freight = float(chosen["freight_usd_per_t"])
    bunker = float(opt.get("bunker_used_usd_t") or 0.0)

    live = _live_vessel(shipment.assigned_mmsi)
    prog = _progress(shipment, live)

    baseline = shipment.baseline_usd_per_t
    drift = round(delivered - baseline, 2) if baseline is not None else None

    result = {
        "ts": _now().isoformat(),
        "vessel_class": chosen["vessel"],
        "delivered_usd_per_t": round(delivered, 2),
        "freight_usd_per_t": round(freight, 2),
        "bunker_usd_t": round(bunker, 1),
        "baseline_usd_per_t": baseline,
        "drift_usd_per_t": drift,
        "drift_pct": (round(drift / baseline * 100, 1)
                      if drift is not None and baseline else None),
        "cargo_cost_usd": round(delivered * float(shipment.cargo_t)),
        "progress_pct": prog["progress_pct"],
        "distance_remaining_nm": prog["distance_remaining_nm"],
        "distance_total_nm": prog["distance_total_nm"],
        "speed_used_kn": prog["speed_used_kn"],
        "eta_ts": prog["eta_ts"],
        "shipments_required": chosen.get("shipments_required"),
    }

    if persist:
        eta = _naive(datetime.fromisoformat(prog["eta_ts"])) if prog["eta_ts"] else None
        with session_scope() as s:
            s.add(ShipmentCost(
                shipment_id=shipment.id,
                delivered_usd_per_t=result["delivered_usd_per_t"],
                freight_usd_per_t=result["freight_usd_per_t"],
                bunker_usd_t=result["bunker_usd_t"],
                drift_usd_per_t=drift,
                progress_pct=result["progress_pct"],
                eta_ts=eta,
                distance_remaining_nm=result["distance_remaining_nm"],
                detail={"vessel_class": chosen["vessel"],
                        "cargo_cost_usd": result["cargo_cost_usd"]},
                run_id=run_id,
            ))
    return result


def _analysis_view(shipment: Shipment, market: MarketData | None = None) -> dict:
    """Route + recommendation + the chosen option + emissions for the detail page."""
    m = market or STORE.require()
    laycan_month = shipment.laycan_start.month if shipment.laycan_start else None
    opt = run_optimise(
        m, shipment.origin_code, shipment.dest_code, shipment.commodity,
        float(shipment.cargo_t), laycan_month=laycan_month,
    )
    chosen = _choose_option(opt, shipment.vessel_class)
    o = port_reg.get(shipment.origin_code)
    d = port_reg.get(shipment.dest_code)
    geom: list[list[float]] = []
    if o and d:
        geom = sea_route(o.lat, o.lon, d.lat, d.lon, o.basin, d.basin).geometry
    return {
        "route": opt.get("route"),
        "recommendation": opt.get("recommendation"),
        "chosen_option": chosen,
        "options": opt.get("options"),
        "emissions": opt.get("emissions"),
        "bunker_used_usd_t": opt.get("bunker_used_usd_t"),
        "route_geometry": geom,
        "ports": {
            "origin": o.to_public() if o else None,
            "destination": d.to_public() if d else None,
        },
    }


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def _resolve_ports_or_raise(origin: str, dest: str) -> None:
    if port_reg.get(origin) is None:
        raise ValueError(f"unknown origin port: {origin!r}")
    if port_reg.get(dest) is None:
        raise ValueError(f"unknown destination port: {dest!r}")


def create(payload: dict) -> dict:
    _resolve_ports_or_raise(payload["origin_code"], payload["dest_code"])
    row = Shipment(
        ref=_gen_ref(),
        commodity=payload.get("commodity") or "Thermal Coal",
        cargo_t=float(payload["cargo_t"]),
        origin_code=payload["origin_code"],
        dest_code=payload["dest_code"],
        vessel_class=payload.get("vessel_class"),
        assigned_mmsi=payload.get("assigned_mmsi"),
        laycan_start=payload.get("laycan_start"),
        laycan_end=payload.get("laycan_end"),
        contract_months=int(payload.get("contract_months") or 6),
        status=payload.get("status") or "planned",
        notes=payload.get("notes"),
    )
    with session_scope() as s:
        s.add(row)
        s.flush()
        # capture the baseline delivered cost at creation, from the same engine
        try:
            val = revalue(row, persist=False)
            row.baseline_usd_per_t = val["delivered_usd_per_t"]
            row.baseline_at = _now()
        except Exception:  # pragma: no cover - never block creation on the engine
            log.exception("baseline valuation failed for %s", row.ref)
        s.flush()
        out = _public(row)
    return out


def list_all() -> list[dict]:
    with session_scope() as s:
        rows = s.scalars(select(Shipment).order_by(desc(Shipment.created_at))).all()
        shipments = [_public(r) for r in rows]
        ids = [r.id for r in rows]
        latest: dict[int, ShipmentCost] = {}
        if ids:
            costs = s.scalars(
                select(ShipmentCost)
                .where(ShipmentCost.shipment_id.in_(ids))
                .order_by(desc(ShipmentCost.ts))
            ).all()
            for c in costs:
                latest.setdefault(c.shipment_id, c)
        by_ref = {r.ref: r.id for r in rows}
    for sh in shipments:
        c = latest.get(by_ref[sh["ref"]])
        sh["latest_cost"] = None if c is None else {
            "ts": c.ts.isoformat() if c.ts else None,
            "delivered_usd_per_t": c.delivered_usd_per_t,
            "drift_usd_per_t": c.drift_usd_per_t,
            "progress_pct": c.progress_pct,
            "eta_ts": c.eta_ts.isoformat() if c.eta_ts else None,
        }
    return shipments


def _get_row(s, ref: str) -> Shipment | None:
    return s.scalars(select(Shipment).where(Shipment.ref == ref)).first()


def get(ref: str) -> dict | None:
    with session_scope() as s:
        row = _get_row(s, ref)
        if row is None:
            return None
        base = _public(row)
        detached = Shipment(**{c.name: getattr(row, c.name) for c in Shipment.__table__.columns})
        costs = s.scalars(
            select(ShipmentCost)
            .where(ShipmentCost.shipment_id == row.id)
            .order_by(ShipmentCost.ts)
        ).all()
        history = [{
            "ts": c.ts.isoformat() if c.ts else None,
            "delivered_usd_per_t": c.delivered_usd_per_t,
            "drift_usd_per_t": c.drift_usd_per_t,
            "bunker_usd_t": c.bunker_usd_t,
            "progress_pct": c.progress_pct,
            "eta_ts": c.eta_ts.isoformat() if c.eta_ts else None,
        } for c in costs]

    live = _live_vessel(detached.assigned_mmsi)
    valuation = revalue(detached, persist=False)
    analysis = _analysis_view(detached)
    return {
        "shipment": base,
        "live_vessel": live,
        "valuation": valuation,
        "analysis": analysis,
        "cost_history": history,
    }


def update(ref: str, patch: dict) -> dict | None:
    fields = {k: v for k, v in patch.items() if v is not None}
    with session_scope() as s:
        row = _get_row(s, ref)
        if row is None:
            return None
        for k in ("status", "assigned_mmsi", "vessel_class", "notes",
                  "contract_months", "laycan_start", "laycan_end"):
            if k in fields:
                setattr(row, k, fields[k])
        if fields.get("rebaseline"):
            try:
                row.baseline_usd_per_t = revalue(row, persist=False)["delivered_usd_per_t"]
                row.baseline_at = _now()
            except Exception:  # pragma: no cover
                log.exception("re-baseline failed for %s", ref)
        s.flush()
        return _public(row)


def delete(ref: str) -> bool:
    with session_scope() as s:
        row = _get_row(s, ref)
        if row is None:
            return False
        s.execute(
            ShipmentCost.__table__.delete().where(ShipmentCost.shipment_id == row.id)
        )
        s.delete(row)
        return True


def revalue_all(market: MarketData | None = None, run_id: int | None = None) -> dict:
    """Value every non-terminal shipment and append a ``shipment_costs`` row.
    Called once per ingest run. Best-effort per shipment."""
    with session_scope() as s:
        rows = [
            Shipment(**{c.name: getattr(r, c.name) for c in Shipment.__table__.columns})
            for r in s.scalars(
                select(Shipment).where(Shipment.status.not_in(_TERMINAL))
            ).all()
        ]
    valued = 0
    errors = 0
    for row in rows:
        try:
            revalue(row, market=market, run_id=run_id, persist=True)
            valued += 1
        except Exception:  # pragma: no cover
            errors += 1
            log.exception("revalue failed for %s", row.ref)
    return {"shipments": len(rows), "valued": valued, "errors": errors}

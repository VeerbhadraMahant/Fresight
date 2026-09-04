"""Forecast / vessel / timing / risk / scenario endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .. import reference_data as ref
from ..decision_backtest import decision_backtest as run_decision_backtest
from ..forecasting import forecast as run_forecast
from ..geo import ports as port_reg
from ..idle_risk import idle_outlook, scan_risks
from ..market_store import STORE
from ..modelled_lane import is_traded
from ..procurement_planner import plan as run_plan
from ..schemas import PlanRequest, ScenarioRequest, TimingRequest, VesselOptimiseRequest
from ..timing import recommend as run_timing
from ..vessel_optimizer import optimise as run_optimise

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/forecast")
def forecast(route_id: str, vessel: str, horizon_days: int = 90):
    m = STORE.require()
    try:
        out = run_forecast(m, route_id, vessel, horizon_days=horizon_days)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, f"cannot build a series for {route_id} / {vessel}: {e}") from e
    out["series_kind"] = "traded" if is_traded(m, route_id, vessel) else "modelled"
    return out


@router.post("/vessel/optimise")
def vessel_optimise(req: VesselOptimiseRequest):
    m = STORE.require()
    try:
        return run_optimise(
            m, req.origin, req.destination, req.commodity, req.cargo_volume_t,
            laycan_month=req.laycan_month,
            use_forecast_horizon_days=req.use_forecast_horizon_days,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/timing/recommend")
def timing_recommend(req: TimingRequest):
    m = STORE.require()
    try:
        return run_timing(
            m, req.route_id, req.vessel,
            contract_duration_months=req.contract_duration_months,
            volume_t=req.volume_t, risk_aversion=req.risk_aversion,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/risk/scan")
def risk_scan(max_alerts: int = 25):
    return scan_risks(STORE.require(), max_alerts=max_alerts)


@router.get("/idle")
def idle(route_id: str, vessel: str):
    m = STORE.require()
    try:
        return idle_outlook(m, route_id, vessel)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/backtest/decisions")
def backtest_decisions(
    route_id: str,
    vessel: str,
    contract_months: int = Query(3, ge=1, le=24),
):
    m = STORE.require()
    try:
        out = run_decision_backtest(m, route_id, vessel, contract_months=contract_months)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    out["series_kind"] = "traded" if is_traded(m, route_id, vessel) else "modelled"
    return out


@router.post("/plan")
def procurement_plan(req: PlanRequest):
    m = STORE.require()
    try:
        return run_plan(m, [r.model_dump() for r in req.requirements],
                        horizon_months=req.horizon_months)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/scenario")
def scenario(req: ScenarioRequest):
    """Run the whole desk for one cargo scenario -- powers the dashboard."""
    m = STORE.require()
    # any resolvable port worldwide -- code, UN/LOCODE, WPI no., name or "lat,lon".
    # curated East-Coast-India lanes keep their calibrated path; everything else
    # falls through to the sea-route + voyage-economics estimate.
    if port_reg.get(req.origin) is None or port_reg.get(req.destination) is None:
        raise HTTPException(400, "unknown port code")

    opt = run_optimise(
        m, req.origin, req.destination, req.commodity, req.cargo_volume_t,
        laycan_month=req.laycan_month,
        use_forecast_horizon_days=req.forecast_horizon_days,
    )
    route_id = opt["route"]["id"]
    vessel = req.vessel or (opt["recommendation"]["vessel"] if opt["recommendation"]
                            else opt["options"][0]["vessel"])

    traded = is_traded(m, route_id, vessel)
    # forecasting / timing / cover-timing now run for ANY resolvable lane: a lane
    # with no traded benchmark gets a modelled (estimate-on-estimate) history.
    fc_horizon = max(req.forecast_horizon_days, req.contract_duration_months * 30 + 60)
    try:
        fc = run_forecast(m, route_id, vessel, horizon_days=fc_horizon)
        tim = run_timing(m, route_id, vessel,
                         contract_duration_months=req.contract_duration_months,
                         volume_t=req.cargo_volume_t, precomputed_fc=fc)
    except (KeyError, ValueError):
        fc = tim = None
    idle = idle_outlook(m, route_id, vessel) if route_id in ref.ROUTES else None
    dbt = None
    try:
        _db = run_decision_backtest(m, route_id, vessel,
                                    contract_months=req.contract_duration_months)
        dbt = {"strategies": _db["strategies"], "summary": _db["summary"],
               "decision_points": _db["decision_points"],
               "limited_history": _db["limited_history"], "note": _db["note"]}
    except ValueError:
        dbt = None
    risks = scan_risks(m, max_alerts=40)
    scoped = [a for a in risks["alerts"]
              if a["scope"].get("route_id") == route_id
              or a["scope"].get("port") in (req.origin, req.destination)
              or a["scope"].get("scope") == "market"
              or a["scope"].get("seasonality_profile") == (ref.ROUTES[route_id].seasonality_profile
                                                           if route_id in ref.ROUTES else None)]

    return {
        "request": req.model_dump(),
        "resolved": {"route_id": route_id, "vessel": vessel,
                     "lane": opt["route"].get("lane"),
                     "has_market_series": traded,
                     "series_kind": "traded" if traded else "modelled"},
        "vessel_optimisation": opt,
        "forecast": fc,
        "timing": tim,
        "idle_outlook": idle,
        "decision_backtest": dbt,
        "weather": m.weather.get(req.destination),
        "risk_alerts": {"scoped": scoped, "all_count": risks["alert_count"],
                        "severity_counts": risks["severity_counts"]},
    }

"""Multi-cargo procurement planner.

Turns a list of forward cargo requirements into a recommended contract mix -- how
much of each lane to lock as a medium-term period / COA contract versus leave to
spot -- with the expected cost and cost-risk of the plan against covering
everything on rolling spot.

This is the problem statement's objective made concrete: the shift from many
single spot fixtures to fewer short/medium-term multiple-voyage contracts.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .forecasting import forecast
from .synthetic import MarketData
from .timing import _annualised_vol
from .vessel_optimizer import optimise

WEEKS_PER_MONTH = 4.345


def plan(market: MarketData, requirements: list[dict],
         horizon_months: int = 6) -> dict:
    if not requirements:
        raise ValueError("no requirements supplied")

    lanes: dict[tuple, list[dict]] = defaultdict(list)
    for r in requirements:
        lanes[(r["origin"], r["destination"], r.get("commodity", "Thermal Coal"))].append(r)

    lane_rows = []
    tot_plan = tot_spot = tot_spot_risk = tot_plan_risk = tot_co2 = 0.0
    for (origin, dest, commodity), reqs in lanes.items():
        tonnes = float(sum(x["tonnes"] for x in reqs))
        opt = optimise(market, origin, dest, commodity, tonnes)
        rec = opt["recommendation"]
        route_id = opt["route"]["id"]
        vessel = rec["vessel"] if rec else opt["options"][0]["vessel"]
        delivered = rec["delivered_cost_usd_per_t"] if rec else opt["options"][0]["delivered_cost_usd_per_t"]

        has_series = (route_id, vessel) in market.freight.columns
        if has_series:
            fc = forecast(market, route_id, vessel,
                          horizon_days=horizon_months * 30 + 40, folds=3)
            k = int(round(horizon_months * WEEKS_PER_MONTH))
            fmeans = [row["mean"] for row in fc["forecast"]][:k] or [delivered]
            exp_spot = float(np.mean(fmeans))
            slope = (fmeans[-1] / fmeans[0] - 1.0) if len(fmeans) > 1 and fmeans[0] else 0.0
            vol = _annualised_vol(market.freight_series(route_id, vessel))
            rmse = fc["backtest"]["ensemble"]["rmse"] or exp_spot * 0.12
            spot_std_t = float(rmse) / np.sqrt(max(k / 3, 1))
        else:
            exp_spot, slope, vol, spot_std_t = delivered, 0.0, 0.2, delivered * 0.12

        # coverage fraction: lock more when the curve slopes up and is volatile
        cover = float(np.clip(0.30 + 1.6 * max(slope, 0.0) + 0.40 * (vol - 0.35), 0.20, 0.80))
        period_rate = 0.5 * delivered + 0.5 * exp_spot   # unbiased mid-market COA

        plan_cost = cover * tonnes * period_rate + (1 - cover) * tonnes * exp_spot
        spot_cost = tonnes * exp_spot
        plan_risk = (1 - cover) * tonnes * spot_std_t
        spot_risk = tonnes * spot_std_t
        co2_kt = (opt["emissions"]["recommended_kt"] if opt.get("emissions") else 0.0) \
            * (tonnes / max(sum(x["tonnes"] for x in reqs), 1))  # already campaign-scaled

        tot_plan += plan_cost
        tot_spot += spot_cost
        tot_plan_risk += plan_risk
        tot_spot_risk += spot_risk
        tot_co2 += co2_kt

        lane_rows.append({
            "route_id": route_id,
            "lane": opt["route"].get("lane"),
            "commodity": commodity,
            "tonnes": round(tonnes),
            "vessel": vessel,
            "period_cover_pct": round(cover * 100),
            "spot_pct": round((1 - cover) * 100),
            "period_rate_usd_t": round(period_rate, 2),
            "expected_spot_usd_t": round(exp_spot, 2),
            "forecast_slope_pct": round(slope * 100, 1),
            "plan_cost_usd": round(plan_cost),
            "all_spot_cost_usd": round(spot_cost),
            "saving_usd": round(spot_cost - plan_cost),
            "co2_kt": round(co2_kt, 1),
        })

    lane_rows.sort(key=lambda r: -r["saving_usd"])
    return {
        "horizon_months": horizon_months,
        "lanes": lane_rows,
        "totals": {
            "plan_cost_usd": round(tot_plan),
            "all_spot_cost_usd": round(tot_spot),
            "expected_saving_usd": round(tot_spot - tot_plan),
            "expected_saving_pct": round((1 - tot_plan / tot_spot) * 100, 2) if tot_spot else 0.0,
            "cost_risk_reduction_usd": round(tot_spot_risk - tot_plan_risk),
            "total_co2_kt": round(tot_co2, 1),
            "tonnes": round(sum(r["tonnes"] for r in lane_rows)),
        },
    }

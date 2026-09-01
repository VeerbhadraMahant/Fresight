"""Idle-scenario management and risk-mitigation alerts.

idle_outlook()  -- for a given lane/vessel, forecast weeks of soft demand and
                   estimate the idle-day / positioning risk, with mitigation
                   options (alternative lanes, discharge-port switch, timing).

scan_risks()    -- sweep the whole dataset for early-warning signals:
                   volatility spikes, port-congestion build-ups, bunker surges,
                   seasonal demand troughs and rate extremes. Returns a
                   severity-ranked alert feed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import reference_data as ref
from .synthetic import MarketData

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


# --------------------------------------------------------------------------- #
def _upcoming_seasonal(profile: str, weeks: int = 12) -> list[tuple[str, float]]:
    today = pd.Timestamp.today().normalize()
    out = []
    for w in range(weeks):
        d = today + pd.Timedelta(weeks=w)
        out.append((d.strftime("%Y-%m-%d"), ref.SEASONALITY[profile][d.month - 1]))
    return out


def idle_outlook(market: MarketData, route_id: str, vessel: str) -> dict:
    route = ref.ROUTES.get(route_id)
    if route is None:
        raise ValueError("unknown route")
    prof = route.seasonality_profile
    seasonal = _upcoming_seasonal(prof, 12)
    dp = route.destination

    cong = market.congestion[dp]
    cong_recent = float(cong.iloc[-14:].mean())
    cong_year = float(cong.iloc[-365:].mean())

    # soft-demand weeks: seasonal factor below its own mean and below 0.98
    vals = np.array([v for _, v in seasonal])
    thresh = min(0.985, float(vals.mean()) - 0.005)
    soft_weeks = [{"week": d, "seasonal_factor": round(v, 3)}
                  for d, v in seasonal if v <= thresh]

    demand_pressure = float(np.clip((1.0 - vals.min()) * 100, 0, 100))
    cong_pressure = float(np.clip((cong_recent / max(cong_year, 0.1) - 1) * 120, 0, 100))
    # weeks in monsoon add structural East Coast idle risk
    monsoon_weeks = sum(1 for d, _ in seasonal if pd.Timestamp(d).month in (6, 7, 8, 9))
    monsoon_pressure = monsoon_weeks / 12 * 100

    idle_index = round(float(np.clip(
        0.4 * demand_pressure + 0.35 * cong_pressure + 0.25 * monsoon_pressure, 0, 100)), 0)
    est_idle_days = round(
        cong_recent * 0.6 + len(soft_weeks) * 0.8 + monsoon_weeks * 0.5, 1)

    # mitigation: alternative *discharge ports* on the East Coast with firmer
    # near-term demand / lower waiting time (a different berth for flexible parcels)
    alt = []
    seen_dest: set[str] = {route.destination}
    for rid, r in ref.ROUTES.items():
        if r.destination in seen_dest or ref.PORTS[r.destination].region != "India-EastCoast":
            continue
        seen_dest.add(r.destination)
        s_alt = _upcoming_seasonal(r.seasonality_profile, 8)
        firmness = float(np.mean([v for _, v in s_alt]))
        alt_cong = float(market.congestion[r.destination].iloc[-14:].mean())
        alt.append({
            "route_id": rid, "lane": r.lane,
            "near_term_demand_factor": round(firmness, 3),
            "discharge_wait_days": round(alt_cong, 2),
            "demand_weight": r.demand_weight,
        })
    alt.sort(key=lambda a: (-a["near_term_demand_factor"], a["discharge_wait_days"]))

    suggestions = []
    if soft_weeks:
        suggestions.append(
            f"{len(soft_weeks)} soft-demand week(s) ahead on this lane -- avoid ballasting "
            f"open into {ref.PORTS[dp].name}; delay positioning or pre-fix a period cargo.")
    if cong_pressure > 30:
        best_alt = alt[0] if alt else None
        if best_alt:
            suggestions.append(
                f"{ref.PORTS[dp].name} waiting time running {cong_recent:.1f} d "
                f"(vs {cong_year:.1f} d yr-avg); consider {best_alt['lane']} "
                f"({best_alt['discharge_wait_days']} d wait) for flexible parcels.")
    if monsoon_weeks >= 4:
        suggestions.append(
            f"{monsoon_weeks} of the next 12 weeks fall in the SW monsoon -- build "
            f"+1-2 weather days into laycans for East Coast discharge and prefer "
            f"geared tonnage where berths congest.")
    if not suggestions:
        suggestions.append("Demand and congestion outlook is benign; normal positioning is fine.")

    return {
        "route_id": route_id,
        "vessel": vessel,
        "lane": route.lane,
        "idle_risk_index": idle_index,
        "estimated_idle_days_next_12w": est_idle_days,
        "components": {
            "demand_pressure": round(demand_pressure, 0),
            "congestion_pressure": round(cong_pressure, 0),
            "monsoon_pressure": round(monsoon_pressure, 0),
        },
        "soft_demand_weeks": soft_weeks,
        "discharge_wait_days_now": round(cong_recent, 2),
        "discharge_wait_days_year_avg": round(cong_year, 2),
        "alternative_lanes": alt[:4],
        "mitigation": suggestions,
    }


# --------------------------------------------------------------------------- #
def _mk(alert_id, category, severity, scope, message, action, metrics):
    return {
        "id": alert_id, "category": category, "severity": severity, "scope": scope,
        "message": message, "recommended_action": action, "metrics": metrics,
        "detected_at": pd.Timestamp.today().strftime("%Y-%m-%d"),
    }


def scan_risks(market: MarketData, max_alerts: int = 25) -> dict:
    alerts: list[dict] = []
    fr = market.freight

    # ---- 1. volatility spikes per lane -------------------------------- #
    for (rid, vessel) in fr.columns:
        s = fr[(rid, vessel)].dropna()
        if len(s) < 400:
            continue
        w = s.resample("W-MON").mean().pct_change().dropna()
        recent = float(w.iloc[-4:].std())
        base = float(w.iloc[-52:].std())
        if base > 0 and recent / base > 1.45 and recent > 0.025:
            sev = "high" if recent / base > 2.0 else "medium"
            alerts.append(_mk(
                f"vol-{rid}-{vessel}", "volatility", sev, {"route_id": rid, "vessel": vessel},
                f"{vessel} {ref.ROUTES[rid].lane}: 4-week volatility {recent*100:.1f}% is "
                f"{recent/base:.1f}x the 12-month norm.",
                "Favour period cover / freight options over new spot exposure on this lane; "
                "widen laycan buffers.",
                {"recent_vol_pct": round(recent * 100, 1), "baseline_vol_pct": round(base * 100, 1),
                 "ratio": round(recent / base, 2)}))

    # ---- 2. port congestion build-up -------------------------------- #
    for code, port in ref.PORTS.items():
        s = market.congestion[code]
        now = float(s.iloc[-10:].mean())
        base = float(s.iloc[-120:-10].mean())
        slope = float(s.iloc[-21:].diff().mean())
        if base > 0 and now / base > 1.3 and slope > 0:
            sev = "high" if now / base > 1.8 or now > 6 else "medium"
            alerts.append(_mk(
                f"cong-{code}", "port_congestion", sev,
                {"port": code, "port_name": port.name, "region": port.region},
                f"{port.name}: waiting time ~{now:.1f} d, {now/base:.1f}x recent norm and rising.",
                "Re-time laycans, pre-advise agents, or divert flexible parcels to a less "
                "congested berth; price demurrage risk into fixtures.",
                {"wait_now_days": round(now, 2), "wait_baseline_days": round(base, 2),
                 "trend_days_per_day": round(slope, 3)}))

    # ---- 3. bunker surge ------------------------------------------- #
    b = market.bunker
    chg_30 = float(b.iloc[-1] / b.iloc[-31] - 1)
    if abs(chg_30) > 0.10:
        sev = "high" if abs(chg_30) > 0.18 else "medium"
        direction = "surged" if chg_30 > 0 else "dropped"
        alerts.append(_mk(
            "bunker-30d", "bunker", sev, {"scope": "market"},
            f"VLSFO has {direction} {chg_30*100:+.1f}% in 30 days to ${b.iloc[-1]:.0f}/t.",
            ("Expect freight to firm on bunker pass-through; accelerate cover decisions."
             if chg_30 > 0 else
             "Bunker relief should ease freight; spot patience may be rewarded."),
            {"vlsfo_now": round(float(b.iloc[-1]), 1), "change_30d_pct": round(chg_30 * 100, 1)}))

    # ---- 4. seasonal demand trough (next 8 weeks) ----------------- #
    for prof in {r.seasonality_profile for r in ref.ROUTES.values()}:
        up = _upcoming_seasonal(prof, 8)
        mn = min(up, key=lambda x: x[1])
        if mn[1] < 0.96:
            alerts.append(_mk(
                f"season-{prof}", "seasonal_demand", "low", {"seasonality_profile": prof},
                f"'{prof}' lanes head into a demand soft-patch (factor {mn[1]:.2f}) around {mn[0]}.",
                "Delay non-urgent positioning; negotiate period cargoes while owners are soft.",
                {"trough_week": mn[0], "seasonal_factor": round(mn[1], 3)}))

    # ---- 5. rate extremes (aggregate market-wide, keep a few standouts) -- #
    highs, lows = [], []
    for (rid, vessel) in fr.columns:
        s = fr[(rid, vessel)].dropna()
        if len(s) < 300:
            continue
        year = s.iloc[-365:]
        pct = float((year < s.iloc[-1]).mean() * 100)
        rec = {"route_id": rid, "vessel": vessel, "lane": ref.ROUTES[rid].lane,
               "percentile_12m": round(pct, 0), "rate_usd_t": round(float(s.iloc[-1]), 2)}
        if pct >= 90:
            highs.append(rec)
        elif pct <= 10:
            lows.append(rec)

    def _extreme_alert(recs, kind):
        if not recs:
            return
        recs.sort(key=lambda r: r["percentile_12m"], reverse=(kind == "high"))
        n_lanes = len(recs)
        if kind == "high":
            sev = "high" if n_lanes >= 6 else "medium"
            head = (f"{n_lanes} lane/vessel combinations are trading at/above the 90th "
                    f"percentile of the last 12 months") if n_lanes > 1 else recs[0]["lane"]
            action = ("Broad-based strength: avoid locking long period cover at the top; "
                      "prefer short spot / freight options and stagger fixtures.")
        else:
            sev = "medium" if n_lanes >= 6 else "low"
            head = (f"{n_lanes} lane/vessel combinations are near 12-month lows") \
                if n_lanes > 1 else recs[0]["lane"]
            action = ("Broad-based weakness: attractive window to secure short/medium-term "
                      "period or COA cover while owners are soft.")
        alerts.append(_mk(
            f"rate-extreme-{kind}", "rate_extreme", sev, {"scope": "market"},
            f"{head}. Standouts: " + "; ".join(
                f"{r['vessel']} {r['lane']} (${r['rate_usd_t']}/t, p{r['percentile_12m']:.0f})"
                for r in recs[:3]) + ".",
            action,
            {"lane_count": n_lanes, "standouts": recs[:5]}))

    _extreme_alert(highs, "high")
    _extreme_alert(lows, "low")

    alerts.sort(key=lambda a: (-SEVERITY_RANK[a["severity"]], a["category"]))
    counts: dict[str, int] = {}
    for a in alerts:
        counts[a["severity"]] = counts.get(a["severity"], 0) + 1
    return {
        "as_of": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "alert_count": len(alerts),
        "severity_counts": counts,
        "alerts": alerts[:max_alerts],
    }

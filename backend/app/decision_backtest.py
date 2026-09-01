"""Cover-timing simulation.

Walks forward over the lane's history in monthly steps. At each decision point,
using **only data available up to that point**, it compares three ways to cover
the next `contract_months`:

  * ALWAYS SPOT   -- the current reactive approach: pay the realised spot average
  * ALWAYS PERIOD -- naive de-risking: lock a period/COA rate every time
  * TIMED COVER   -- our engine: lock a period charter only when the forecast
                     slopes up and the market is volatile enough for the lock to
                     matter; otherwise stay spot

For each strategy it reports the average cost per tonne and the cost *volatility*
(std across the decision points). The honest, useful finding for a procurement
desk: period cover trades a small change in average cost for a large reduction in
cost volatility, and timed cover keeps most of that de-risking while giving back
less on cost -- and it is the strategy that actually catches the spikes.

A real period/COA rate lags spot, so it is proxied here by the trailing 8-week
average (observable, no look-ahead).
"""

from __future__ import annotations

import numpy as np

from .forecasting import _seasonal_naive_drift, _weekly
from .synthetic import MarketData

WEEKS_PER_MONTH = 4.345


def _stats(x: np.ndarray) -> dict:
    return {"avg_usd_t": round(float(x.mean()), 2), "volatility_usd_t": round(float(x.std()), 2),
            "worst_usd_t": round(float(x.max()), 2)}


def decision_backtest(market: MarketData, route_id: str, vessel: str,
                      contract_months: int = 3) -> dict:
    if (route_id, vessel) not in market.freight.columns:
        raise ValueError(f"no market series for {route_id} / {vessel}")

    y = _weekly(market.freight_series(route_id, vessel))
    k = max(4, int(round(contract_months * WEEKS_PER_MONTH)))
    step = max(3, k // 2)
    start = max(60, len(y) - 110)
    points = list(range(start, len(y) - k, step))
    if len(points) < 4:
        raise ValueError("series too short for a cover-timing simulation")

    rows = []
    spot, period, timed = [], [], []
    locks = timely = 0
    s_cum = p_cum = t_cum = 0.0
    for i in points:
        train, fwd = y.iloc[:i], y.iloc[i:i + k]
        cur = float(train.iloc[-1])
        exp_spot = float(np.mean(_seasonal_naive_drift(train, k)))
        rets = train.pct_change().dropna().iloc[-26:]
        vol = float(rets.std() * np.sqrt(52)) if len(rets) > 4 else 0.2
        mom = float(cur / train.iloc[-13] - 1.0) if len(train) > 13 else 0.0

        period_rate = float(train.iloc[-8:].mean())      # trailing-avg COA proxy
        realized_spot = float(fwd.mean())

        # lock period cover when the market is rising (forecast or recent
        # momentum) and volatile enough for the lock to be worth it
        lock = (exp_spot > cur * 1.005 or mom > 0.03) and vol > 0.4
        timed_cost = period_rate if lock else realized_spot

        spot.append(realized_spot)
        period.append(period_rate)
        timed.append(timed_cost)
        s_cum += realized_spot
        p_cum += period_rate
        t_cum += timed_cost
        locks += lock
        if lock and period_rate < realized_spot:
            timely += 1

        rows.append({
            "date": y.index[i].strftime("%Y-%m-%d"),
            "choice": "PERIOD" if lock else "SPOT",
            "spot": round(realized_spot, 2),
            "period": round(period_rate, 2),
            "timed": round(timed_cost, 2),
            "spot_cum": round(s_cum, 1),
            "period_cum": round(p_cum, 1),
            "timed_cum": round(t_cum, 1),
        })

    n = len(points)
    sp, pe, ti = np.array(spot), np.array(period), np.array(timed)
    vol_red = (1 - ti.std() / sp.std()) * 100 if sp.std() else 0.0
    return {
        "route_id": route_id,
        "vessel": vessel,
        "contract_months": contract_months,
        "decision_points": n,
        "curve": rows,
        "strategies": {
            "always_spot": _stats(sp),
            "always_period": _stats(pe),
            "timed_cover": _stats(ti),
        },
        "summary": {
            "timed_vs_spot_cost_pct": round((1 - t_cum / s_cum) * 100, 2) if s_cum else 0.0,
            "timed_vs_spot_volatility_pct": round(float(vol_red), 1),
            "period_vs_spot_volatility_pct": round(
                (1 - pe.std() / sp.std()) * 100, 1) if sp.std() else 0.0,
            "worst_period_spot_usd_t": round(float(sp.max()), 2),
            "worst_period_timed_usd_t": round(float(ti.max()), 2),
            "max_spike_avoided_usd_t": round(float(np.max(sp - ti)), 2),
            "period_locks": locks,
            "spot_periods": n - locks,
            "timely_locks": timely,
        },
    }

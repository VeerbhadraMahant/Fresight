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
_MIN_TRAIN_WEEKS = 52   # history required before the first decision point
_MIN_DECISIONS = 4     # fewest walk-forward points for a meaningful cost/vol stat


def _stats(x: np.ndarray) -> dict:
    return {"avg_usd_t": round(float(x.mean()), 2), "volatility_usd_t": round(float(x.std()), 2),
            "worst_usd_t": round(float(x.max()), 2)}


def decision_backtest(market: MarketData, route_id: str, vessel: str,
                      contract_months: int = 3) -> dict:
    # market.freight_series() supplies a modelled history for non-traded lanes
    y = _weekly(market.freight_series(route_id, vessel))
    k = max(4, int(round(contract_months * WEEKS_PER_MONTH)))

    # Each decision point i needs _MIN_TRAIN_WEEKS of history behind it and a full
    # k-week realised window ahead: i in [_MIN_TRAIN_WEEKS, len(y) - k).
    lo, hi = _MIN_TRAIN_WEEKS, len(y) - k
    if hi - lo < _MIN_DECISIONS:
        raise ValueError("series too short for a cover-timing simulation")

    # Prefer the most recent ~110 weeks so results stay stable for short contracts.
    step = max(3, k // 2)
    points = list(range(max(lo, len(y) - 110), hi, step))
    if len(points) < _MIN_DECISIONS:
        # A long contract eats the recent window -- reach back over all usable
        # history and shrink the step (forward windows then overlap, as is normal
        # for a rolling back-test) until _MIN_DECISIONS points fit.
        span = hi - lo
        step = min(max(3, k // 3), max(1, span // _MIN_DECISIONS))
        points = list(range(lo, hi, step))
        if len(points) < _MIN_DECISIONS:                # rounding guard
            step = max(1, span // _MIN_DECISIONS)
            points = list(range(lo, hi, step))

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

    def _vol_red_pct(x: np.ndarray) -> float:
        # "% less volatile than always-spot"; clamp to [-100, 100] -- with few,
        # heavily-overlapping windows sp.std() -> ~0 and the raw ratio explodes.
        if not sp.std():
            return 0.0
        return round(float(max(-100.0, min(100.0, (1 - x.std() / sp.std()) * 100))), 1)

    # too few walk-forward windows fit this contract length -> weak vol stats
    limited = n < 6

    return {
        "route_id": route_id,
        "vessel": vessel,
        "contract_months": contract_months,
        "decision_points": n,
        "limited_history": limited,
        "note": (
            "Few non-overlapping windows fit this contract length in the available "
            "history; treat the volatility figures as indicative."
            if limited else None
        ),
        "curve": rows,
        "strategies": {
            "always_spot": _stats(sp),
            "always_period": _stats(pe),
            "timed_cover": _stats(ti),
        },
        "summary": {
            "timed_vs_spot_cost_pct": round((1 - t_cum / s_cum) * 100, 2) if s_cum else 0.0,
            "timed_vs_spot_volatility_pct": _vol_red_pct(ti),
            "period_vs_spot_volatility_pct": _vol_red_pct(pe),
            "worst_period_spot_usd_t": round(float(sp.max()), 2),
            "worst_period_timed_usd_t": round(float(ti.max()), 2),
            "max_spike_avoided_usd_t": round(float(np.max(sp - ti)), 2),
            "period_locks": locks,
            "spot_periods": n - locks,
            "timely_locks": timely,
        },
    }

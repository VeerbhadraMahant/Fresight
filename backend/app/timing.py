"""Market-entry timing and spot-vs-period charter recommendation.

Consumes the freight forecast and turns it into chartering actions:

  * Optimal entry window -- the near-term week where expected cost of *fixing*
    the charter is lowest, given the forecast path and its downside band.
  * Spot vs period -- expected cost and risk of covering the requirement with
    rolling spot fixtures versus one short/medium-term period charter, with a
    recommendation that accounts for both expected cost and cost variance.
  * Saving vs the current reactive approach -- benchmark against repeatedly
    fixing single spot voyages at today's level.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import reference_data as ref
from .forecasting import forecast
from .synthetic import MarketData

WEEKS_PER_MONTH = 4.345


def _annualised_vol(series: pd.Series) -> float:
    w = series.resample("W-MON").mean().pct_change().dropna()
    return float(w.std() * np.sqrt(52)) if len(w) > 4 else 0.0


def recommend(market: MarketData, route_id: str, vessel: str,
              contract_duration_months: int = 3, volume_t: float = 150_000,
              risk_aversion: float = 0.35, precomputed_fc: dict | None = None) -> dict:
    if vessel not in ref.VESSEL_CLASSES:
        raise ValueError(f"unknown vessel class {vessel!r}")
    # market.freight_series() supplies a modelled history for non-traded lanes

    contract_weeks = int(round(contract_duration_months * WEEKS_PER_MONTH))
    horizon_days = max(200, contract_duration_months * 30 + 60)
    fc = precomputed_fc or forecast(market, route_id, vessel, horizon_days=horizon_days, folds=4)

    hist = market.freight_series(route_id, vessel)
    current = float(hist.iloc[-1])
    vol = _annualised_vol(hist)

    fmeans = np.array([r["mean"] for r in fc["forecast"]])
    flo = np.array([r["lo"] for r in fc["forecast"]])
    fdates = [r["date"] for r in fc["forecast"]]

    # ---- optimal entry window (look at first 12 weeks) ------------------ #
    look = min(12, len(fmeans))
    seg_mean = fmeans[:look]
    seg_lo = flo[:look]
    trough_i = int(np.argmin(seg_mean))
    trough_val = float(seg_mean[trough_i])
    rel_drop = (current - trough_val) / current

    if rel_drop > 0.025 and seg_lo[trough_i] < current * 1.02 and trough_i >= 1:
        entry_action = "WAIT"
        lo_i, hi_i = max(0, trough_i - 1), min(look - 1, trough_i + 1)
        entry_window = {"from": fdates[lo_i], "to": fdates[hi_i],
                        "weeks_out": trough_i + 1}
        entry_saving_usd = round((current - trough_val) * volume_t)
        entry_rationale = (
            f"Forecast dips ~{rel_drop*100:.1f}% to ~${trough_val:.1f}/t about "
            f"{trough_i+1} week(s) out; downside band stays near today's level, so "
            f"waiting to fix is favourable.")
    else:
        entry_action = "FIX_NOW"
        entry_window = {"from": fdates[0], "to": fdates[min(1, look - 1)], "weeks_out": 0}
        entry_saving_usd = 0
        entry_rationale = (
            "Forecast offers no material near-term dip (or the downside risk of "
            "waiting outweighs it); securing tonnage now is preferable.")

    # ---- spot vs period ---------------------------------------------- #
    k = min(contract_weeks, len(fmeans))
    exp_spot_avg = float(np.mean(fmeans[:k]))
    # spot cost variance over the contract: residual RMSE from the backtest,
    # scaled down by averaging over k independent-ish weeks
    rmse = fc["backtest"]["ensemble"]["rmse"] or (vol * current / np.sqrt(52))
    spot_std_per_t = float(rmse) / np.sqrt(max(k / 3.0, 1.0))

    slope = (fmeans[k - 1] - fmeans[0]) / max(fmeans[0], 1e-6) if k > 1 else 0.0
    # owners price a period fixture off the forward expectation plus a liquidity
    # premium that widens with volatility and with an upward-sloping curve
    liq_premium = 0.012 + 0.05 * max(slope, 0.0) + 0.25 * vol * 0.02
    period_rate = (0.45 * current + 0.55 * exp_spot_avg) * (1 + liq_premium)
    period_std_per_t = 0.15 * spot_std_per_t  # largely locked in

    spot_cost = exp_spot_avg * volume_t
    period_cost = period_rate * volume_t
    spot_risk = spot_std_per_t * volume_t
    period_risk = period_std_per_t * volume_t

    # risk-adjusted comparison
    spot_ra = spot_cost + risk_aversion * spot_risk
    period_ra = period_cost + risk_aversion * period_risk
    if period_ra < spot_ra:
        charter_choice = "PERIOD"
        charter_rationale = (
            f"A {contract_duration_months}-month period charter at ~${period_rate:.1f}/t "
            f"has a lower risk-adjusted cost than rolling spot (exp. ${exp_spot_avg:.1f}/t "
            f"but ±${spot_std_per_t:.1f}/t). "
            + ("Upward-sloping forecast favours locking in. " if slope > 0.02 else "")
            + "Removes exposure to freight spikes over the cover period.")
    else:
        charter_choice = "SPOT"
        charter_rationale = (
            f"Rolling spot (exp. ${exp_spot_avg:.1f}/t) beats the period offer "
            f"(~${period_rate:.1f}/t) on a risk-adjusted basis; forecast is flat/soft "
            f"and the period premium ({liq_premium*100:.1f}%) is not justified.")

    # ---- vs current reactive approach ------------------------------ #
    # "Reactive" = keep fixing single spot voyages over the cover period, i.e.
    # you ride the forecast spot path (exp_spot_avg) and carry its variance.
    reactive_cost = spot_cost
    reactive_risk = spot_risk
    chosen_cost = period_cost if charter_choice == "PERIOD" else spot_cost
    chosen_risk = period_risk if charter_choice == "PERIOD" else spot_risk
    saving_vs_reactive = round(reactive_cost - chosen_cost)
    risk_reduction_vs_reactive = round(reactive_risk - chosen_risk)
    # reference-only: what it would cost if today's rate simply held flat
    flat_reference_cost = round(current * volume_t)

    return {
        "route_id": route_id,
        "vessel": vessel,
        "as_of": fc["as_of"],
        "current_rate_usd_t": round(current, 2),
        "annualised_volatility_pct": round(vol * 100, 1),
        "forecast_slope_over_contract_pct": round(slope * 100, 1),
        "entry_timing": {
            "action": entry_action,
            "window": entry_window,
            "expected_saving_usd": entry_saving_usd,
            "rationale": entry_rationale,
        },
        "charter_structure": {
            "recommendation": charter_choice,
            "contract_duration_months": contract_duration_months,
            "spot": {
                "expected_rate_usd_t": round(exp_spot_avg, 2),
                "expected_cost_usd": round(spot_cost),
                "cost_std_usd": round(spot_risk),
            },
            "period": {
                "indicative_rate_usd_t": round(period_rate, 2),
                "expected_cost_usd": round(period_cost),
                "cost_std_usd": round(period_risk),
                "liquidity_premium_pct": round(liq_premium * 100, 2),
            },
            "rationale": charter_rationale,
        },
        "vs_reactive_spot_approach": {
            "reactive_expected_cost_usd": round(reactive_cost),
            "reactive_cost_std_usd": round(reactive_risk),
            "recommended_expected_cost_usd": round(chosen_cost),
            "recommended_cost_std_usd": round(chosen_risk),
            "expected_saving_usd": saving_vs_reactive,
            "expected_saving_pct": round(saving_vs_reactive / reactive_cost * 100, 2) if reactive_cost else 0.0,
            "risk_reduction_usd": risk_reduction_vs_reactive,
            "flat_rate_reference_cost_usd": flat_reference_cost,
            "note": (
                "Reactive = rolling single spot voyages over the cover period (exposed to "
                "the forecast path). 'flat_rate_reference' is only what today's rate held "
                "constant would cost -- shown for context, not an achievable plan."
            ),
        },
        "forecast_preview": fc["monthly"],
        "backtest": fc["backtest"],
    }

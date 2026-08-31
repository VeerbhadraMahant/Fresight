"""Freight-rate forecasting.

Ensemble of two complementary models on a weekly-resampled series:

  1. Holt-Winters exponential smoothing (damped additive trend + additive
     yearly seasonality) -- captures level, momentum and the restocking /
     monsoon cycle.
  2. Seasonal-naive-with-drift -- last year's weekly pattern, re-based to the
     current level and nudged by the recent drift. Robust when (1) over-fits.

The ensemble is the mean of the two. Skill is measured by rolling-origin
back-testing (expanding window, weekly step): MAPE, RMSE and bias are reported
for the ensemble and each component. Prediction intervals come from the
back-test residual distribution, widened with the square root of the horizon.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager

import numpy as np
import pandas as pd

from .synthetic import MarketData

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tools.sm_exceptions import ConvergenceWarning, ValueWarning
    _HAS_SM = True
except Exception:  # pragma: no cover
    _HAS_SM = False
    ConvergenceWarning = ValueWarning = Warning


@contextmanager
def _quiet_solver():
    """Silence the noisy-but-expected optimiser warnings from a single fit,
    without suppressing warnings process-wide."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", ValueWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        yield

WEEK = "W-MON"
SEASON_WEEKS = 52
MIN_TRAIN_WEEKS = 120


# --------------------------------------------------------------------------- #
def _weekly(y: pd.Series) -> pd.Series:
    return y.resample(WEEK).mean().interpolate("linear").dropna()


def _fit_holt_winters(train: pd.Series, steps: int) -> np.ndarray:
    if _HAS_SM and len(train) >= 2 * SEASON_WEEKS + 4:
        with _quiet_solver():
            model = ExponentialSmoothing(
                train, trend="add", damped_trend=True,
                seasonal="add", seasonal_periods=SEASON_WEEKS,
                initialization_method="estimated",
            )
            fit = model.fit(optimized=True)
            return np.asarray(fit.forecast(steps), dtype=float)
    # fallback: damped linear trend on last 26 weeks
    tail = train.iloc[-26:]
    x = np.arange(len(tail))
    slope, intercept = np.polyfit(x, tail.to_numpy(), 1)
    last = len(tail) - 1
    return intercept + slope * (last + 0.6 * np.arange(1, steps + 1))


def _seasonal_naive_drift(train: pd.Series, steps: int) -> np.ndarray:
    if len(train) >= SEASON_WEEKS + 8:
        last_year = train.iloc[-SEASON_WEEKS:].to_numpy()
        recent_level = train.iloc[-8:].mean()
        year_ago_level = train.iloc[-SEASON_WEEKS - 8:-SEASON_WEEKS].mean() if len(train) >= SEASON_WEEKS + 16 else recent_level
        rebase = recent_level / max(year_ago_level, 1e-6)
        drift = np.polyfit(np.arange(12), train.iloc[-12:].to_numpy(), 1)[0]
        out = []
        for h in range(1, steps + 1):
            base = last_year[(h - 1) % SEASON_WEEKS] * rebase
            out.append(base + drift * h * 0.4)
        return np.asarray(out, dtype=float)
    return np.repeat(train.iloc[-4:].mean(), steps)


def _ensemble_forecast(train: pd.Series, steps: int) -> dict[str, np.ndarray]:
    hw = _fit_holt_winters(train, steps)
    sn = _seasonal_naive_drift(train, steps)
    ens = 0.5 * hw + 0.5 * sn
    return {"holt_winters": hw, "seasonal_naive": sn, "ensemble": ens}


# --------------------------------------------------------------------------- #
def _rolling_backtest(y: pd.Series, folds: int, fold_horizon: int) -> dict:
    n = len(y)
    results: dict[str, list[float]] = {"holt_winters": [], "seasonal_naive": [], "ensemble": []}
    resid_pool: list[float] = []
    first_train = max(MIN_TRAIN_WEEKS, n - folds * fold_horizon - fold_horizon)
    starts = list(range(first_train, n - fold_horizon + 1, fold_horizon))[-folds:]
    for s in starts:
        train, test = y.iloc[:s], y.iloc[s:s + fold_horizon]
        if len(test) < 2:
            continue
        fc = _ensemble_forecast(train, len(test))
        for name, pred in fc.items():
            err = test.to_numpy() - pred
            mape = float(np.mean(np.abs(err / np.clip(test.to_numpy(), 1e-6, None))) * 100)
            rmse = float(np.sqrt(np.mean(err ** 2)))
            bias = float(np.mean(err))
            results[name].append((mape, rmse, bias))
        resid_pool.extend((test.to_numpy() - fc["ensemble"]).tolist())

    def agg(rows: list[tuple]) -> dict:
        if not rows:
            return {"mape": None, "rmse": None, "bias": None}
        arr = np.array(rows)
        return {"mape": round(float(arr[:, 0].mean()), 2),
                "rmse": round(float(arr[:, 1].mean()), 2),
                "bias": round(float(arr[:, 2].mean()), 2)}

    resid_std = float(np.std(resid_pool)) if resid_pool else float(y.pct_change().std() * y.mean())
    return {
        "folds": len(starts),
        "fold_horizon_weeks": fold_horizon,
        "ensemble": agg(results["ensemble"]),
        "models": {k: agg(v) for k, v in results.items() if k != "ensemble"},
        "residual_std": resid_std,
    }


# --------------------------------------------------------------------------- #
def _driver_diagnostics(market: MarketData, route_id: str, vessel: str) -> dict:
    df = market.feature_frame(route_id, vessel).tail(365)
    w = df.resample(WEEK).mean()
    r = w["rate"]

    def corr(col: str) -> float | None:
        if col not in w or w[col].std() == 0:
            return None
        return round(float(r.corr(w[col])), 2)

    trend_30 = None
    if len(r) >= 5:
        trend_30 = round(float((r.iloc[-1] / r.iloc[-5] - 1) * 100), 1)
    return {
        "bunker_corr": corr("bunker"),
        "tce_corr": corr("tce"),
        "congestion_load_corr": corr("cong_load"),
        "congestion_disch_corr": corr("cong_disch"),
        "commodity_index_corr": corr("commodity_index"),
        "trend_pct_last_30d": trend_30,
    }


_CACHE: dict[tuple, dict] = {}


def forecast(market: MarketData, route_id: str, vessel: str,
             horizon_days: int = 90, folds: int = 4) -> dict:
    # the market dataset is built once at startup and is immutable thereafter,
    # so results can be memoised for the life of the process (keyed by dataset id)
    key = (id(market), route_id, vessel, horizon_days, folds)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    out = _forecast_impl(market, route_id, vessel, horizon_days, folds)
    _CACHE[key] = out
    return out


def _forecast_impl(market: MarketData, route_id: str, vessel: str,
                   horizon_days: int, folds: int) -> dict:
    y_daily = market.freight_series(route_id, vessel)
    if y_daily.empty:
        raise ValueError(f"no market series for {route_id} / {vessel}")
    y = _weekly(y_daily)
    steps = max(4, int(round(horizon_days / 7)))

    bt = _rolling_backtest(y, folds=folds, fold_horizon=max(6, steps))
    fc = _ensemble_forecast(y, steps)
    mean = fc["ensemble"]

    resid_std = bt["residual_std"]
    h = np.arange(1, steps + 1)
    widen = resid_std * np.sqrt(h) * 0.55 + resid_std * 0.6
    lo, hi = mean - 1.28 * widen, mean + 1.28 * widen  # ~80% interval
    lo = np.clip(lo, 0.2 * y.mean(), None)

    fdates = pd.date_range(y.index[-1] + pd.Timedelta(weeks=1), periods=steps, freq=WEEK)
    forecast_rows = [
        {"date": d.strftime("%Y-%m-%d"), "mean": round(float(m), 2),
         "lo": round(float(l), 2), "hi": round(float(hh), 2)}
        for d, m, l, hh in zip(fdates, mean, lo, hi)
    ]

    fc_series = pd.Series(mean, index=fdates)
    lo_series = pd.Series(lo, index=fdates)
    hi_series = pd.Series(hi, index=fdates)
    monthly = []
    for month, grp in fc_series.groupby(fc_series.index.to_period("M")):
        monthly.append({
            "month": str(month),
            "mean": round(float(grp.mean()), 2),
            "lo": round(float(lo_series[grp.index].mean()), 2),
            "hi": round(float(hi_series[grp.index].mean()), 2),
        })

    hist_tail = y.iloc[-96:]
    history_rows = [{"date": d.strftime("%Y-%m-%d"), "rate": round(float(v), 2)}
                    for d, v in hist_tail.items()]

    trailing_year = y.iloc[-52:]
    pct = float((trailing_year < y.iloc[-1]).mean() * 100)
    prof = None
    from . import reference_data as ref
    sp = ref.ROUTES[route_id].seasonality_profile
    seasonal_now = ref.SEASONALITY[sp][pd.Timestamp.today().month - 1]

    def horizon_mean(days: int) -> float:
        k = max(1, int(round(days / 7)))
        return round(float(np.mean(mean[:k])), 2)

    return {
        "route_id": route_id,
        "vessel": vessel,
        "as_of": y.index[-1].strftime("%Y-%m-%d"),
        "latest_rate": round(float(y.iloc[-1]), 2),
        "horizon_days": horizon_days,
        "model": "HoltWinters(damped) + SeasonalNaiveDrift ensemble",
        "history": history_rows,
        "forecast": forecast_rows,
        "monthly": monthly,
        "expected_rate": {
            "next_30d": horizon_mean(30),
            "next_60d": horizon_mean(60),
            "next_90d": horizon_mean(90),
        },
        "current_percentile_12m": round(pct, 0),
        "seasonal_factor_now": round(float(seasonal_now), 3),
        "backtest": {k: v for k, v in bt.items() if k != "residual_std"},
        "drivers": _driver_diagnostics(market, route_id, vessel),
    }

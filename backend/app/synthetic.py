"""Synthetic market engine.

Generates a self-consistent multi-year daily history for:
  * VLSFO bunker price (macro driver)
  * time-charter-equivalent (TCE) hire per vessel class
  * port congestion queues (waiting days) per port
  * freight rate in USD/tonne per route x vessel class
  * auxiliary macro drivers (commodity price index, industrial-production proxy)

The freight series is anchored to the bottom-up voyage-economics model
(`voyage_economics.fundamental_freight_usd_t`) so the numbers stay physically
plausible, then given realistic stochastic dynamics:
  - mean reversion to a slowly drifting long-run level
  - regime-switching volatility (calm / normal / stressed markets)
  - an annual seasonal cycle (Indian coal restocking + SW-monsoon weather)
  - occasional demand shocks (both signs)
  - route "basis" noise so routes don't move in lockstep
  - an additive congestion cost pass-through

Everything is seeded, so the dataset is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import reference_data as ref
from .voyage_economics import estimate_voyage

SEED = 20260831
HISTORY_YEARS = 3.5
TODAY = pd.Timestamp("2026-08-31")


# --------------------------------------------------------------------------- #
@dataclass
class MarketData:
    freight: pd.DataFrame      # index=date, columns=MultiIndex(route_id, vessel) -> USD/t
    bunker: pd.Series          # index=date -> USD/t VLSFO
    tce: pd.DataFrame          # index=date, columns=vessel -> USD/day
    congestion: pd.DataFrame   # index=date, columns=port_code -> waiting days
    drivers: pd.DataFrame      # index=date, columns=[commodity_index, global_ip, sentiment]
    generated_at: pd.Timestamp = field(default_factory=lambda: pd.Timestamp.utcnow())
    source: str = "synthetic-engine-v1"

    # ---- convenience accessors ------------------------------------------- #
    def freight_series(self, route_id: str, vessel: str) -> pd.Series:
        return self.freight[(route_id, vessel)].dropna()

    def latest_freight(self, route_id: str, vessel: str) -> float:
        return float(self.freight_series(route_id, vessel).iloc[-1])

    def feature_frame(self, route_id: str, vessel: str) -> pd.DataFrame:
        """Assemble the modelling frame for one route x vessel."""
        r = ref.ROUTES[route_id]
        y = self.freight_series(route_id, vessel).rename("rate")
        df = pd.DataFrame(index=y.index)
        df["rate"] = y
        df["bunker"] = self.bunker.reindex(y.index).ffill()
        df["tce"] = self.tce[vessel].reindex(y.index).ffill()
        df["cong_load"] = self.congestion[r.origin].reindex(y.index).ffill()
        df["cong_disch"] = self.congestion[r.destination].reindex(y.index).ffill()
        df["commodity_index"] = self.drivers["commodity_index"].reindex(y.index).ffill()
        df["global_ip"] = self.drivers["global_ip"].reindex(y.index).ffill()
        df["sentiment"] = self.drivers["sentiment"].reindex(y.index).ffill()
        month = df.index.month
        prof = ref.SEASONALITY[r.seasonality_profile]
        df["seasonal"] = [prof[m - 1] for m in month]
        df["doy_sin"] = np.sin(2 * np.pi * df.index.dayofyear / 365.25)
        df["doy_cos"] = np.cos(2 * np.pi * df.index.dayofyear / 365.25)
        return df


# --------------------------------------------------------------------------- #
def _ar1(n: int, rho: float, sigma: float, rng: np.random.Generator, x0: float = 0.0) -> np.ndarray:
    out = np.empty(n)
    x = x0
    for i in range(n):
        x = rho * x + rng.normal(0.0, sigma)
        out[i] = x
    return out


def _regime_vol(n: int, rng: np.random.Generator) -> np.ndarray:
    """Markov regime switch between calm(0.6x) / normal(1x) / stressed(2.2x) vol."""
    states = np.array([0.6, 1.0, 2.2])
    # transition matrix (persistent regimes)
    P = np.array([
        [0.985, 0.014, 0.001],
        [0.010, 0.975, 0.015],
        [0.004, 0.046, 0.950],
    ])
    s = 1
    out = np.empty(n)
    for i in range(n):
        s = rng.choice(3, p=P[s])
        out[i] = states[s]
    return out


def _seasonal_vector(dates: pd.DatetimeIndex, profile: str) -> np.ndarray:
    prof = ref.SEASONALITY[profile]
    return np.array([prof[m - 1] for m in dates.month])


# --------------------------------------------------------------------------- #
def _inject_recent_events(freight: pd.DataFrame, vlsfo: pd.Series,
                          congestion: pd.DataFrame, tce: pd.DataFrame,
                          rng: np.random.Generator) -> None:
    """Overlay a few plausible near-term events on the last ~6 weeks."""
    n = len(freight)
    idx = freight.index

    # (a) congestion build-up at Paradip over the last 18 days
    k = n - 18
    ramp = np.linspace(0, 4.5, n - k)
    congestion.iloc[k:, congestion.columns.get_loc("INPRT")] += ramp
    # freight on Paradip-discharge lanes reflects the demurrage pressure
    for col in freight.columns:
        if col[0].endswith("INPRT"):
            freight.iloc[k:, freight.columns.get_loc(col)] *= (1 + ramp / 140.0)

    # (b) bunker uptick over the last 24 days (+11%)
    k = n - 24
    bump = np.linspace(0, 0.11, n - k)
    vlsfo.iloc[k:] = vlsfo.iloc[k:].to_numpy() * (1 + bump)

    # (c) a volatile stretch on two Indonesia lanes (Supramax/Panamax) - last 5 wks
    k = n - 35
    for rid in ("IDMBR-INVTZ", "IDMBR-INPRT"):
        for vessel in ("Supramax", "Panamax"):
            col = (rid, vessel)
            if col not in freight.columns:
                continue
            j = freight.columns.get_loc(col)
            shocks = rng.normal(0, 0.035, n - k).cumsum()
            freight.iloc[k:, j] = freight.iloc[k:, j].to_numpy() * (1 + shocks) * \
                (1 + np.linspace(0, 0.09, n - k))


def generate(seed: int = SEED) -> MarketData:
    rng = np.random.default_rng(seed)
    start = (TODAY - pd.Timedelta(days=int(HISTORY_YEARS * 365.25))).normalize()
    dates = pd.date_range(start, TODAY, freq="D")
    n = len(dates)
    t = np.arange(n)

    # ---- macro: bunker (VLSFO) price -------------------------------------- #
    # mean-reverting to a slowly-drifting anchor, with fat-tailed shocks
    anchor = ref.BUNKER_ANCHOR_USD_T * (1.0 + 0.06 * np.sin(2 * np.pi * (t / 365.25 + 0.15))
                                        + 0.00010 * t)
    dev = _ar1(n, rho=0.992, sigma=6.0, rng=rng)
    # occasional geopolitical bunker spikes
    for _ in range(rng.integers(3, 6)):
        k = rng.integers(0, n)
        mag = rng.uniform(40, 120) * rng.choice([1, 1, -1])
        decay = np.exp(-np.arange(n - k) / rng.uniform(25, 60))
        dev[k:] += mag * decay
    vlsfo = pd.Series(np.clip(anchor + dev, 320, None), index=dates, name="vlsfo_usd_t")

    # ---- macro drivers -------------------------------------------------- #
    commodity_index = 100 + np.cumsum(_ar1(n, 0.98, 0.35, rng)) + 8 * np.sin(2 * np.pi * t / 365.25)
    global_ip = 100 + 3.0 * np.sin(2 * np.pi * (t / 365.25 + 0.35)) + np.cumsum(_ar1(n, 0.97, 0.05, rng))
    sentiment = np.tanh(_ar1(n, 0.95, 0.18, rng))  # -1 bearish .. +1 bullish
    drivers = pd.DataFrame(
        {"commodity_index": commodity_index, "global_ip": global_ip, "sentiment": sentiment},
        index=dates,
    )

    # ---- TCE hire per vessel class ------------------------------------- #
    vol = _regime_vol(n, rng)
    tce = {}
    # a shared dry-bulk demand cycle so classes are correlated but not identical
    common_cycle = _ar1(n, 0.995, 0.010, rng)
    for name in ref.VESSEL_ORDER:
        vc = ref.VESSEL_CLASSES[name]
        base = vc.typical_tce_usd_day
        idio = _ar1(n, 0.99, 0.012, rng)
        seas = _seasonal_vector(dates, "monsoon")
        shock = np.zeros(n)
        for _ in range(rng.integers(4, 8)):
            k = rng.integers(0, n)
            mag = rng.uniform(0.15, 0.55) * rng.choice([1, -1])
            decay = np.exp(-np.arange(n - k) / rng.uniform(20, 70))
            shock[k:] += mag * decay
        mult = np.exp(0.9 * common_cycle + idio) * seas * (1 + shock) * (1 + 0.02 * vol * rng.standard_normal(n))
        series = np.clip(base * mult, base * 0.35, base * 3.2)
        tce[name] = series
    tce = pd.DataFrame(tce, index=dates)

    # ---- port congestion (waiting days) ------------------------------- #
    congestion = {}
    for code, port in ref.PORTS.items():
        seas = _seasonal_vector(dates, "monsoon")
        # monsoon (Jun-Sep) worsens East-Coast-India queues; scale swing by 1/seasonal
        swing = np.where(np.isin(dates.month, [6, 7, 8, 9]), 1.6, 1.0) if port.region == "India-EastCoast" else 1.0
        base = port.congestion_base_days
        ar = _ar1(n, 0.97, 0.05, rng)
        q = base * swing * (1 + 0.25 * ar)
        for _ in range(rng.integers(2, 6)):
            k = rng.integers(0, n)
            dur = rng.integers(6, 22)
            q[k:k + dur] += rng.uniform(1.5, 5.0)
        congestion[code] = np.clip(q, 0.2, None)
    congestion = pd.DataFrame(congestion, index=dates)

    # ---- freight rate per route x vessel ----------------------------- #
    cols = {}
    for route_id, route in ref.ROUTES.items():
        # route-level basis noise (persistent) so lanes decorrelate a bit
        basis = _ar1(n, 0.985, 0.006, rng)
        route_seas = _seasonal_vector(dates, route.seasonality_profile)
        for vessel in ref.VESSEL_ORDER:
            vc = ref.VESSEL_CLASSES[vessel]
            lp, dp = ref.PORTS[route.origin], ref.PORTS[route.destination]
            # skip physically impossible pairings (kept out of the dataset entirely)
            gov_draft = min(lp.max_draft_m, dp.max_draft_m)
            if vc.scantling_draft > gov_draft + 4.0 and not (lp.transload or dp.transload):
                # e.g. Capesize into Haldia -- no market exists
                continue
            fund = np.empty(n)
            # vectorised-ish: recompute the voyage estimate on a monthly grid, interpolate
            grid_idx = np.arange(0, n, 15)
            gvals = []
            for gi in grid_idx:
                vb = estimate_voyage(route, vc, float(vlsfo.iloc[gi]), float(tce[vessel].iloc[gi]))
                gvals.append(vb.freight_usd_t)
            fund = np.interp(t, grid_idx, gvals)

            # congestion pass-through: waiting days priced at the vessel's TCE, spread over cargo
            cong_days = (congestion[route.origin].to_numpy() + congestion[route.destination].to_numpy())
            intake = estimate_voyage(route, vc, ref.BUNKER_ANCHOR_USD_T, vc.typical_tce_usd_day).cargo_t
            cong_cost_t = cong_days * tce[vessel].to_numpy() / max(intake, 1.0)

            noise = _ar1(n, 0.9, 1.0, rng) * (0.010 * fund) * vol
            level = (fund * route_seas / route_seas.mean()) * (1 + basis) + cong_cost_t + noise
            level = np.clip(level, 0.35 * fund, 3.5 * fund)
            cols[(route_id, vessel)] = level

    freight = pd.DataFrame(cols, index=dates)
    freight.columns = pd.MultiIndex.from_tuples(freight.columns, names=["route_id", "vessel"])

    # ---- deterministic "current conditions" so the live risk feed has -- #
    # something to show on demo day (a congestion event, a bunker move, a
    # couple of volatile lanes). These are recent-window only.
    _inject_recent_events(freight, vlsfo, congestion, tce, rng)

    return MarketData(
        freight=freight, bunker=vlsfo, tce=tce, congestion=congestion, drivers=drivers,
        generated_at=pd.Timestamp.utcnow(),
    )

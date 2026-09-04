"""Synthesise a plausible freight-rate history for a lane that has no traded
benchmark, so forecasting / timing / cover-timing work for *any* port pair.

A calibrated lane (one of the ~16 in :data:`reference_data.ROUTES`) carries a
real-modelled series built by :mod:`app.synthetic`. For every other resolvable
pair we build one on demand:

    level   = this lane's bottom-up voyage-economics fundamental (USD/t now)
    shape   = the dry-bulk cycle every lane rides -- taken as the mean of the
              traded series for the same vessel class, normalised to mean 1
    season  = the route's monsoon / flat seasonal profile
    noise   = small AR(1) wobble, deterministically seeded from the lane id

The result is flagged ``modelled`` everywhere it surfaces: it is an estimate on
an estimate, not a traded index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import reference_data as ref
from .synthetic import MarketData, _ar1, _seasonal_vector
from .voyage_economics import estimate_voyage

# per-MarketData cache: (route_id, vessel) -> Series
_CACHE_ATTR = "_modelled_cache"


def route_of(route_id: str):
    """The calibrated :class:`ref.Route`, or a synthesised one for any pair."""
    if route_id in ref.ROUTES:
        return ref.ROUTES[route_id]
    origin, dest = _split_route_id(route_id)
    from .vessel_optimizer import resolve_route  # local -> avoid import cycle

    return resolve_route(origin, dest)


def _split_route_id(route_id: str) -> tuple[str, str]:
    origin, sep, dest = route_id.rpartition("-")
    if not sep:
        raise ValueError(f"route id {route_id!r} is not '<origin>-<destination>'")
    return origin, dest


def is_traded(market: MarketData, route_id: str, vessel: str) -> bool:
    return (route_id, vessel) in market.freight.columns


def series_for(market: MarketData, route_id: str, vessel: str) -> pd.Series:
    """Weekly (calendar-daily, forward-filled) USD/t history for the lane.

    Returns the traded series when there is one, else a modelled series (cached
    on the ``MarketData`` instance so a single scenario reuses it)."""
    if is_traded(market, route_id, vessel):
        return market.freight_series(route_id, vessel)

    cache: dict = getattr(market, _CACHE_ATTR, None) or {}
    key = (route_id, vessel)
    if key in cache:
        return cache[key]

    if vessel not in ref.VESSEL_CLASSES:
        raise ValueError(f"unknown vessel class {vessel!r}")

    idx = market.freight.index
    rte = route_of(route_id)
    vc = ref.VESSEL_CLASSES[vessel]

    # --- shape: the shared dry-bulk cycle for this vessel class ------------- #
    same_vessel = [c for c in market.freight.columns if c[1] == vessel]
    if same_vessel:
        shape = market.freight[same_vessel].mean(axis=1)
    else:  # no traded lane for this class at all -> use every lane
        shape = market.freight.mean(axis=1)
    shape = (shape / shape.mean()).to_numpy()

    # --- level: this lane's fundamental now -------------------------------- #
    fund_now = estimate_voyage(
        rte, vc, float(market.bunker.iloc[-1]), float(market.tce[vessel].iloc[-1])
    ).freight_usd_t

    # --- seasonal + deterministic noise ---------------------------------- #
    seas = _seasonal_vector(idx, rte.seasonality_profile)
    seas = seas / seas.mean()
    seed = abs(hash((route_id, vessel))) % (2**32)
    noise = _ar1(len(idx), rho=0.86, sigma=0.014, rng=np.random.default_rng(seed))

    level = fund_now * shape * seas * (1.0 + noise)
    s = pd.Series(level, index=idx, name="rate").clip(lower=1.0)

    cache[key] = s
    setattr(market, _CACHE_ATTR, cache)
    return s

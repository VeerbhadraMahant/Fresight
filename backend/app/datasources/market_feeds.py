"""Freight-index and bunker feeds from the Yahoo Finance chart API (keyless)."""

from __future__ import annotations

import logging

import pandas as pd

from .base import get_json

log = logging.getLogger("freightsight.datasources")

_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"

# Global VLSFO ~= a * Brent + b  (USD/t vs USD/bbl). Calibrated to 2024-25:
# Brent ~USD 80/bbl -> VLSFO ~USD 580/t ; Brent ~USD 92 -> ~USD 670.
VLSFO_A = 7.4
VLSFO_B = -12.0


def _yahoo_series(symbol: str, rng: str = "5y") -> pd.Series | None:
    data = get_json(_CHART.format(sym=symbol), params={"range": rng, "interval": "1d"})
    try:
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        close = res["indicators"]["quote"][0]["close"]
        s = pd.Series(close, index=pd.to_datetime(ts, unit="s").normalize(), name=symbol)
        return s.dropna().groupby(level=0).last()
    except Exception as exc:
        log.warning("yahoo parse failed for %s: %s", symbol, exc)
        return None


def dry_bulk_freight_index() -> pd.Series | None:
    """BDRY -- Breakwave Dry Bulk Shipping ETF -- a tradeable dry-bulk freight proxy."""
    return _yahoo_series("BDRY")


def brent_crude() -> pd.Series | None:
    """Brent front-month (BZ=F), USD/bbl."""
    return _yahoo_series("BZ%3DF")


def vlsfo_from_brent(brent: pd.Series) -> pd.Series:
    return (brent * VLSFO_A + VLSFO_B).rename("vlsfo_usd_t")

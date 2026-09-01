"""Daily port activity from IMF PortWatch (AIS-derived, keyless ArcGIS API).

Gives, per port, a *real* busy-ness signal (cargo port calls) and a *real*
throughput signal (import tonnes) that we turn into congestion-waiting-days and
demand weights.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .base import get_json

log = logging.getLogger("freightsight.datasources")

_FS = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
    "Daily_Ports_Data/FeatureServer/0/query"
)
_START = "2024-01-01"


def port_activity(name_hint: str) -> pd.DataFrame | None:
    """Daily frame indexed by date with columns: portcalls_cargo, import_t."""
    params = {
        "where": f"portname LIKE '%{name_hint}%' AND date >= DATE '{_START}'",
        "outFields": "date,portname,portcalls,portcalls_cargo,import",
        "orderByFields": "date ASC",
        "resultRecordCount": 2000,
        "f": "json",
    }
    data = get_json(_FS, params=params, timeout=30.0, retries=1)
    try:
        rows = data["features"]
        if not rows:
            return None
        recs = [f["attributes"] for f in rows]
        df = pd.DataFrame(recs)
        # PortWatch dateOnly fields serialize as 'YYYY-MM-DD' strings
        df["date"] = pd.to_datetime(df["date"], format="mixed").dt.normalize()
        df = (df.set_index("date").sort_index()
              .rename(columns={"import": "import_t", "portcalls_cargo": "portcalls_cargo"}))
        df = df[["portcalls_cargo", "import_t"]].astype(float)
        # collapse any duplicate port matches on the same day
        df = df.groupby(level=0).mean()
        return df if len(df) > 60 else None
    except Exception as exc:
        log.warning("PortWatch parse failed for '%s': %s", name_hint, exc)
        return None


def congestion_days(df: pd.DataFrame, base_days: float) -> pd.Series:
    """Real cargo-call intensity vs the port's own 60-day norm -> waiting days."""
    calls = df["portcalls_cargo"].clip(lower=0)
    norm = calls.rolling(60, min_periods=20).median().replace(0, np.nan).ffill().bfill()
    ratio = (calls / norm).clip(0.3, 3.0)
    smoothed = ratio.ewm(span=7).mean()
    return (base_days * smoothed ** 0.85).rename("congestion_days")


def demand_index(df: pd.DataFrame) -> pd.Series:
    """30-day import throughput, normalised to its own mean (1.0 = typical)."""
    imp = df["import_t"].clip(lower=0).rolling(30, min_periods=10).mean()
    return (imp / imp.mean()).rename("demand_index")

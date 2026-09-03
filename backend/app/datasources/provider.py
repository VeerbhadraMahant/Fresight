"""Assembles the real-data bundle the market model blends in.

Two layers:
  * a committed **snapshot** (`app/data/real_snapshot.json`) of every feed, so
    the app always has real numbers -- in CI, offline, or when an API is slow;
  * an optional **live refresh** that overlays fresher values when the public
    APIs are reachable within a short budget.

Feeds (all keyless, public):
  BDRY        Breakwave Dry Bulk Shipping ETF        Yahoo Finance
  Brent->VLSFO  Brent crude front month              Yahoo Finance
  port activity  daily cargo calls + import tonnes   IMF PortWatch
  weather      16-day precip / wind forecast         Open-Meteo
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .. import reference_data as ref
from .market_feeds import brent_crude, dry_bulk_freight_index, vlsfo_from_brent
from .port_activity import congestion_days, demand_index, port_activity
from .weather import weather_outlook

log = logging.getLogger("freightsight.datasources")

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "real_snapshot.json"
LIVE_BUDGET_S = float(os.getenv("FREIGHTSIGHT_LIVE_REFRESH_BUDGET", "12"))

_PORTWATCH_HINT = {
    "INPRT": "Paradip", "INVTZ": "Visakhapatnam", "INGVR": "Gangavaram",
    "INGPR": "Gopalpur", "INDHA": "Dhamra", "INHAL": "Haldia",
    "AUHPT": "Hay Point", "AUNTL": "Newcastle",
}


@dataclass
class RealData:
    dry_bulk_index: pd.Series | None = None
    vlsfo: pd.Series | None = None
    port_congestion: dict[str, pd.Series] = field(default_factory=dict)
    port_demand: dict[str, pd.Series] = field(default_factory=dict)
    weather: dict[str, dict] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    snapshot_date: str | None = None

    def any_live(self) -> bool:
        return any("live" in str(v) or "snapshot" in str(v) for v in self.sources.values())


def _s(d: dict | None) -> pd.Series | None:
    if not d:
        return None
    return pd.Series(d, dtype=float).pipe(lambda s: s.set_axis(pd.to_datetime(s.index))).sort_index()


def _ser(s: pd.Series | None) -> dict | None:
    if s is None:
        return None
    return {d.strftime("%Y-%m-%d"): round(float(v), 4) for d, v in s.items() if v == v}


def _apply_snapshot_dict(rd: RealData, snap: dict) -> None:
    """Load a snapshot dict (same shape as ``real_snapshot.json``) into ``rd``."""
    rd.snapshot_date = (snap.get("built_at") or "")[:10] or None
    rd.dry_bulk_index = _s(snap.get("dry_bulk_index"))
    rd.vlsfo = _s(snap.get("vlsfo"))
    for code, ser in (snap.get("port_congestion") or {}).items():
        rd.port_congestion[code] = _s(ser)
    for code, ser in (snap.get("port_demand") or {}).items():
        rd.port_demand[code] = _s(ser)
    rd.weather = dict(snap.get("weather") or {})


def snapshot_dict(rd: RealData) -> dict:
    """Serialise a RealData back to the ``real_snapshot.json`` shape (for the worker)."""
    return {
        "built_at": (rd.snapshot_date or "") + "T00:00:00Z" if rd.snapshot_date else "",
        "dry_bulk_index": _ser(rd.dry_bulk_index),
        "vlsfo": _ser(rd.vlsfo),
        "port_congestion": {k: _ser(v) for k, v in rd.port_congestion.items()},
        "port_demand": {k: _ser(v) for k, v in rd.port_demand.items()},
        "weather": dict(rd.weather),
    }


def _from_snapshot_file(rd: RealData) -> bool:
    try:
        snap = json.loads(SNAPSHOT.read_text())
    except Exception as exc:
        log.warning("no real-data snapshot file (%s)", exc)
        return False
    _apply_snapshot_dict(rd, snap)
    return True


def _from_snapshot_db(rd: RealData) -> bool:
    """Seed from the freshest ``feed_snapshots`` row the ingest worker wrote."""
    try:
        from ..db import DB_ENABLED, session_scope
        from ..db.models import FeedSnapshot
    except Exception:  # pragma: no cover - db layer optional
        return False
    if not DB_ENABLED:
        return False
    try:
        from sqlalchemy import select

        with session_scope() as s:
            row = s.scalars(
                select(FeedSnapshot)
                .where(FeedSnapshot.feed == "realdata", FeedSnapshot.ok.is_(True))
                .order_by(FeedSnapshot.fetched_at.desc())
                .limit(1)
            ).first()
            if row is None or not row.payload:
                return False
            _apply_snapshot_dict(rd, row.payload)
            log.info("real-data seeded from DB snapshot (as_of %s)", rd.snapshot_date)
            return True
    except Exception as exc:  # pragma: no cover - network dependent
        log.info("DB snapshot unavailable (%s); falling back to file", str(exc)[:120])
        return False


def _from_snapshot(rd: RealData, *, prefer_db: bool = True) -> None:
    if prefer_db and _from_snapshot_db(rd):
        return
    _from_snapshot_file(rd)


def _live_refresh(rd: RealData) -> set[str]:
    """Best-effort overlay of fresher values; returns which components refreshed."""
    fresh: set[str] = set()
    deadline = time.time() + LIVE_BUDGET_S
    jobs = {
        "freight_index": dry_bulk_freight_index,
        "bunker": lambda: (lambda b: vlsfo_from_brent(b) if b is not None else None)(brent_crude()),
    }
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fn): name for name, fn in jobs.items()}
        # a couple of the most-watched discharge ports + weather
        for code in ("INPRT", "INHAL"):
            futs[ex.submit(port_activity, _PORTWATCH_HINT[code])] = f"port:{code}"
        for code in ref.DISCHARGE_PORTS:
            p = ref.PORTS[code]
            futs[ex.submit(weather_outlook, p.lat, p.lon)] = f"wx:{code}"
        try:
            for fut in cf.as_completed(list(futs), timeout=max(1.0, deadline - time.time())):
                name = futs[fut]
                try:
                    res = fut.result(timeout=1)
                except Exception:
                    res = None
                if res is None:
                    continue
                if name == "freight_index":
                    rd.dry_bulk_index = res
                    fresh.add("freight_index")
                elif name == "bunker":
                    rd.vlsfo = res
                    fresh.add("bunker")
                elif name.startswith("port:"):
                    code = name.split(":")[1]
                    base = ref.PORTS[code].congestion_base_days
                    rd.port_congestion[code] = congestion_days(res, base)
                    rd.port_demand[code] = demand_index(res)
                    fresh.add("port_activity")
                elif name.startswith("wx:"):
                    rd.weather[name.split(":")[1]] = res
                    fresh.add("weather")
                if time.time() > deadline:
                    break
        except (TimeoutError, cf.TimeoutError):
            pass
        for fut in futs:
            fut.cancel()
    return fresh


def load_real_data(live_refresh: bool = True, prefer_db: bool = True) -> RealData:
    """Real-data bundle for the market model.

    Source order: the ingest worker's freshest ``feed_snapshots`` row (when a
    database is configured) -> the committed ``real_snapshot.json`` -> optionally
    overlaid with a short direct live refresh.

    Set FREIGHTSIGHT_DISABLE_REALDATA=1 to skip even the snapshot (pure synthetic).
    """
    rd = RealData()
    if os.getenv("FREIGHTSIGHT_DISABLE_REALDATA", "").strip() in {"1", "true", "yes"}:
        rd.sources = dict.fromkeys(
            ("freight_index", "bunker", "port_activity", "weather"), "disabled")
        return rd

    _from_snapshot(rd, prefer_db=prefer_db)
    fresh = _live_refresh(rd) if (live_refresh and rd.snapshot_date) else set()

    def _tag(comp: str, have: bool) -> str:
        if not have:
            return "synthetic"
        return "live (refreshed)" if comp in fresh else f"snapshot {rd.snapshot_date}"

    rd.sources = {
        "freight_index": _tag("freight_index", rd.dry_bulk_index is not None),
        "bunker": _tag("bunker", rd.vlsfo is not None),
        "port_activity": (
            f"{_tag('port_activity', bool(rd.port_congestion))} - {len(rd.port_congestion)} ports"),
        "weather": (
            f"{_tag('weather', bool(rd.weather))} - {len(rd.weather)} ports"),
    }
    log.info("real-data: %s", rd.sources)
    return rd

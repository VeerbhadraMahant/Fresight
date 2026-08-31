"""Market data provider.

On startup, makes a best-effort fetch of *public* Baltic Dry Index values and
records them as a sanity reference (shown in the dashboard header). If the
network is unavailable or a page changes shape, it falls back cleanly and runs
fully offline. Either way the app serves a complete, self-consistent dataset.

The live points are reference-only -- the historical series, back-tests and
forecasts are entirely driven by the offline voyage-economics + stochastic
engine (`synthetic.py`), calibrated to published 2024-25 route rates.

Set FREIGHTSIGHT_SKIP_LIVE_PROBE=1 to disable the outbound request entirely.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from .synthetic import MarketData, generate

log = logging.getLogger("freightsight.market")

# Skip the outbound probe entirely (e.g. locked-down deploy) with
# FREIGHTSIGHT_SKIP_LIVE_PROBE=1. The app is fully functional without it.
_SKIP_PROBE = os.getenv("FREIGHTSIGHT_SKIP_LIVE_PROBE", "").strip() in {"1", "true", "yes"}
_PROBE_TIMEOUT = float(os.getenv("FREIGHTSIGHT_PROBE_TIMEOUT", "4.0"))

_PUBLIC_SOURCES = [
    # (label, url, regex capturing a numeric value, plausible (lo, hi) range)
    ("Baltic Dry Index", "https://tradingeconomics.com/commodity/baltic",
     r'Baltic (?:Dry|Exchange Dry) Index[^0-9]{0,40}?([0-9]{3,5}(?:\.[0-9]+)?)', (400, 6000)),
    ("Baltic Dry Index (handybulk)", "https://www.handybulk.com/baltic-dry-index/",
     r'Baltic Dry Index[^0-9]{0,80}?([0-9]{3,5}(?:\.[0-9]+)?)', (400, 6000)),
]


@dataclass
class Provenance:
    mode: str = "synthetic"                       # "synthetic" | "synthetic+live-anchor"
    live_points: list[dict] = field(default_factory=list)
    attempted: list[str] = field(default_factory=list)
    generated_at: str = ""
    note: str = ""


def _try_public_sources(timeout: float = _PROBE_TIMEOUT) -> list[dict]:
    found: list[dict] = []
    headers = {"User-Agent": "Mozilla/5.0 (FreightSight prototype; +https://sih)"}
    for label, url, pattern, (lo, hi) in _PUBLIC_SOURCES:
        try:
            r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            r.raise_for_status()
            m = re.search(pattern, r.text, re.IGNORECASE | re.DOTALL)
            if m and lo <= float(m.group(1)) <= hi:
                found.append({"label": label, "url": url, "value": float(m.group(1)),
                              "unit": "index", "role": "reference-only",
                              "fetched_at": datetime.now(timezone.utc).isoformat()})
                log.info("live source ok: %s = %s", label, m.group(1))
            elif m:
                log.warning("live source %s value %s outside plausible range", label, m.group(1))
        except Exception as exc:  # noqa: BLE001 - best effort only
            log.warning("live source failed (%s): %s", label, exc)
    return found


class MarketStore:
    """Singleton holder for the generated market dataset."""

    def __init__(self) -> None:
        self.data: MarketData | None = None
        self.provenance = Provenance()

    def build(self) -> None:
        live = []
        attempted = [] if _SKIP_PROBE else [label for label, *_ in _PUBLIC_SOURCES]
        if _SKIP_PROBE:
            log.info("live-source probe disabled (FREIGHTSIGHT_SKIP_LIVE_PROBE)")
        else:
            try:
                live = _try_public_sources()
            except Exception as exc:  # noqa: BLE001
                log.warning("public source probe crashed: %s", exc)

        self.data = generate()
        self.provenance = Provenance(
            mode="synthetic+live-anchor" if live else "synthetic",
            live_points=live,
            attempted=attempted,
            generated_at=datetime.now(timezone.utc).isoformat(),
            note=(
                "All series (history, back-tests, forecasts) are produced by the offline "
                "voyage-economics + stochastic engine, calibrated to published 2024-25 "
                "route rates and real port constraints. "
                + ("Live public indices below were reachable and are shown as a sanity "
                   "reference for demo day; they do not alter the modelled series."
                   if live else
                   "Live public indices were unreachable; running fully offline.")
            ),
        )
        log.info("market dataset built: %s rows, mode=%s",
                 len(self.data.freight), self.provenance.mode)

    def require(self) -> MarketData:
        if self.data is None:
            self.build()
        assert self.data is not None
        return self.data


STORE = MarketStore()

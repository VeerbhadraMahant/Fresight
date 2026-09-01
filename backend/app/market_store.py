"""Market data provider.

Builds the market dataset by blending:
  * real public feeds -- Breakwave dry-bulk freight index, Brent->VLSFO, IMF
    PortWatch port activity, Open-Meteo weather (see `datasources/`) -- from a
    committed snapshot, refreshed live when the APIs are reachable; and
  * the offline voyage-economics + stochastic engine (`synthetic.py`) that
    turns those drivers into a full route x vessel history calibrated to
    published 2024-25 route rates and real port constraints.

Startup is instant (snapshot); a background thread then does a short live
refresh and swaps in the updated dataset.

Set FREIGHTSIGHT_SKIP_LIVE_PROBE=1 to skip all outbound requests (snapshot +
synthetic only) -- the default inside the container.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .datasources import load_real_data
from .synthetic import MarketData, generate

log = logging.getLogger("freightsight.market")

_SKIP_PROBE = os.getenv("FREIGHTSIGHT_SKIP_LIVE_PROBE", "").strip() in {"1", "true", "yes"}


@dataclass
class Provenance:
    mode: str = "synthetic"                     # "hybrid" | "synthetic"
    data_sources: dict[str, str] = field(default_factory=dict)
    snapshot_date: str | None = None
    refreshing: bool = False
    generated_at: str = ""
    note: str = ""

    # kept for backwards-compat with the dashboard header
    live_points: list[dict] = field(default_factory=list)
    attempted: list[str] = field(default_factory=list)


def _note(mode: str, refreshing: bool) -> str:
    base = (
        "Freight rates follow the real Breakwave dry-bulk index; bunkers track Brent; "
        "port congestion comes from IMF PortWatch daily port-activity data; weather-delay "
        "risk uses live Open-Meteo forecasts. A voyage-economics model plus a stochastic "
        "overlay turns these drivers into a per route x vessel history calibrated to "
        "published 2024-25 route rates and real port constraints."
    )
    if mode == "synthetic":
        return ("Real feeds unavailable -- running the offline voyage-economics + stochastic "
                "engine only, calibrated to published 2024-25 route rates.")
    return base + (" Live refresh in progress." if refreshing else "")


class MarketStore:
    """Singleton holder for the generated market dataset."""

    def __init__(self) -> None:
        self.data: MarketData | None = None
        self.provenance = Provenance()
        self._lock = threading.Lock()

    def build(self) -> None:
        real = load_real_data(live_refresh=False)   # instant: committed snapshot
        data = generate(real=real)
        will_refresh = not _SKIP_PROBE and real.snapshot_date is not None
        self._install(data, refreshing=will_refresh)
        log.info("market dataset built: %d series, mode=%s, sources=%s",
                 data.freight.shape[1], self.provenance.mode, data.provenance)

        if will_refresh:
            threading.Thread(target=self._background_refresh, daemon=True,
                             name="realdata-refresh").start()

    def _background_refresh(self) -> None:
        try:
            real = load_real_data(live_refresh=True)
            data = generate(real=real)
            self._install(data, refreshing=False)
            log.info("market dataset refreshed: sources=%s", data.provenance)
        except Exception as exc:
            log.warning("background refresh failed: %s", exc)
            with self._lock:
                self.provenance.refreshing = False

    def _install(self, data: MarketData, *, refreshing: bool) -> None:
        live = any(v not in ("synthetic", "disabled", "") and "synthetic" not in str(v)
                   for v in data.provenance.values())
        mode = "hybrid" if live else "synthetic"
        with self._lock:
            self.data = data
            self.provenance = Provenance(
                mode=mode,
                data_sources=dict(data.provenance),
                snapshot_date=data.real_snapshot_date,
                refreshing=refreshing,
                generated_at=datetime.now(UTC).isoformat(),
                note=_note(mode, refreshing),
            )

    def require(self) -> MarketData:
        if self.data is None:
            self.build()
        assert self.data is not None
        return self.data


STORE = MarketStore()

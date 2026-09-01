"""One-off: fetch every real feed patiently and snapshot it to
`app/data/real_snapshot.json`, committed so the app always has real data to
blend even when the live APIs are slow/unreachable (CI, demo, offline).

Run:  python scripts/build_real_snapshot.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import reference_data as ref
from app.datasources.market_feeds import (
    brent_crude,
    dry_bulk_freight_index,
    vlsfo_from_brent,
)
from app.datasources.port_activity import congestion_days, demand_index, port_activity
from app.datasources.provider import _PORTWATCH_HINT
from app.datasources.weather import weather_outlook

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "real_snapshot.json"


def _ser(s) -> dict:
    return {d.strftime("%Y-%m-%d"): round(float(v), 4) for d, v in s.items() if v == v}


def main() -> None:
    snap: dict = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    print("BDRY...", flush=True)
    bdry = dry_bulk_freight_index()
    snap["dry_bulk_index"] = _ser(bdry) if bdry is not None else None

    print("Brent...", flush=True)
    brent = brent_crude()
    snap["vlsfo"] = _ser(vlsfo_from_brent(brent)) if brent is not None else None

    snap["port_congestion"], snap["port_demand"] = {}, {}
    for code, hint in _PORTWATCH_HINT.items():
        print(f"PortWatch {hint}...", flush=True)
        for attempt in range(3):
            df = port_activity(hint)
            if df is not None:
                base = ref.PORTS[code].congestion_base_days
                snap["port_congestion"][code] = _ser(congestion_days(df, base))
                snap["port_demand"][code] = _ser(demand_index(df))
                break
            time.sleep(3 * (attempt + 1))

    snap["weather"] = {}
    for code in ref.DISCHARGE_PORTS:
        p = ref.PORTS[code]
        print(f"Open-Meteo {p.name}...", flush=True)
        for attempt in range(3):
            w = weather_outlook(p.lat, p.lon)
            if w is not None:
                snap["weather"][code] = w
                break
            time.sleep(3 * (attempt + 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=1))
    print(f"\nwrote {OUT}")
    print("  freight_index:", "yes" if snap["dry_bulk_index"] else "NO")
    print("  vlsfo:", "yes" if snap["vlsfo"] else "NO")
    print("  port_congestion:", list(snap["port_congestion"]))
    print("  weather:", list(snap["weather"]))


if __name__ == "__main__":
    main()

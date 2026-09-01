"""Capture the boot endpoints into `frontend/src/fixtures/demo.ts`.

The dashboard renders this fixture instantly on load (so it is never empty, even
on a Render free-tier cold start) and then swaps in live data when the API
responds.

Run with the API up:  python backend/scripts/capture_demo_fixture.py
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.request
from pathlib import Path

BASE = os.getenv("FREIGHTSIGHT_API", "http://127.0.0.1:8000")
OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "fixtures" / "demo.ts"

DEFAULT = {
    "origin": "AUHPT", "destination": "INPRT", "commodity": "Thermal Coal",
    "cargo_volume_t": 600000, "contract_duration_months": 6, "laycan_month": 11,
    "vessel": None, "forecast_horizon_days": 120,
}


def _get(path: str):
    return json.load(urllib.request.urlopen(BASE + path, timeout=60))


def _post(path: str, body: dict):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> None:
    data = {
        "capturedAt": datetime.datetime.now(datetime.UTC).isoformat(),
        "scenarioRequest": DEFAULT,
        "ports": _get("/api/reference/ports"),
        "vessels": _get("/api/reference/vessels"),
        "routes": _get("/api/reference/routes"),
        "provenance": _get("/api/reference/market/provenance"),
        "snapshot": _get("/api/reference/market/snapshot"),
        "scenario": _post("/api/scenario", DEFAULT),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "// AUTO-GENERATED demo fixture (backend/scripts/capture_demo_fixture.py).\n"
        "// A pre-computed Hay Point -> Paradip scenario, shown instantly on load so\n"
        "// the dashboard is never empty; replaced by live data when the API responds.\n"
        "export const DEMO = " + json.dumps(data, indent=1) + ";\n",
        encoding="utf-8",
    )
    rec = data["scenario"]["vessel_optimisation"]["recommendation"]["vessel"]
    print(f"wrote {OUT}  ({len(json.dumps(data)) // 1024} KB) — reco={rec}, mode={data['provenance']['mode']}")


if __name__ == "__main__":
    main()

"""AISStream.io adapter: parse messages (pure) + sample the live stream (I/O).

AISStream delivers newline-free JSON frames over a single WebSocket:

    {"MessageType": "PositionReport",
     "MetaData": {"MMSI": 244660000, "ShipName": "…", "time_utc": "2026-09-03 10:11:12.3 +0000 UTC"},
     "Message": {"PositionReport": {"Latitude": 51.9, "Longitude": 4.1,
                                    "Sog": 12.4, "Cog": 89.0, "TrueHeading": 90,
                                    "NavigationalStatus": 0}}}

``parse_message`` has no I/O so it is unit-tested against canned frames; the
sampler is a thin, best-effort shell around it. No API key -> ``sample`` is a
no-op that returns an empty, ``ok=False`` bundle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

log = logging.getLogger("freightsight.ais")

AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"
_DEFAULT_SECONDS = 150
_GLOBAL_BBOX = [[[-90.0, -180.0], [90.0, 180.0]]]
_WANT_TYPES = ["PositionReport", "ShipStaticData"]

_NAV_STATUS = {
    0: "under way (engine)", 1: "at anchor", 2: "not under command",
    3: "restricted manoeuvrability", 4: "constrained by draught", 5: "moored",
    6: "aground", 7: "engaged in fishing", 8: "under way (sailing)",
}


@dataclass
class AisPosition:
    mmsi: int
    ts: datetime
    lat: float
    lon: float
    sog_kn: float | None = None
    cog_deg: float | None = None
    heading_deg: float | None = None
    nav_status: str | None = None


@dataclass
class AisStatic:
    mmsi: int
    name: str | None = None
    imo: int | None = None
    ship_type: int | None = None
    destination: str | None = None
    eta_raw: str | None = None
    draft_m: float | None = None
    loa_m: float | None = None
    beam_m: float | None = None


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _f(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _sog(v) -> float | None:
    f = _f(v)
    return None if f is None or f < 0 or f >= 102.3 else f  # 102.3 == not available


def _cog(v) -> float | None:
    f = _f(v)
    return None if f is None or f < 0 or f >= 360.0 else f  # 360.0 == not available


def _heading(v) -> float | None:
    f = _f(v)
    return None if f is None or f < 0 or f >= 511.0 else f % 360.0  # 511 == not available


def _meta_ts(meta: dict) -> datetime:
    raw = (meta or {}).get("time_utc") or ""
    # "2026-09-03 10:11:12.3 +0000 UTC" -> take the leading "YYYY-MM-DD HH:MM:SS"
    head = raw[:19]
    try:
        return datetime.strptime(head, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return datetime.now(UTC)


def _eta(v) -> str | None:
    """AIS ETA object {Month, Day, Hour, Minute} -> "MM-DD HH:MM" (year is not sent)."""
    if not isinstance(v, dict):
        return None
    mo, d, h, mi = v.get("Month"), v.get("Day"), v.get("Hour"), v.get("Minute")
    if not mo or not d:
        return None
    return f"{int(mo):02d}-{int(d):02d} {int(h or 0):02d}:{int(mi or 0):02d}"


def _clean(s) -> str | None:
    if not isinstance(s, str):
        return None
    s = s.strip().strip("@").strip()
    return s or None


def is_dry_bulk(ship_type: int | None) -> bool:
    """AIS ship-type 70-79 == 'Cargo' (bulk carriers are not separately coded)."""
    return ship_type is not None and 70 <= ship_type <= 79


# --------------------------------------------------------------------------- #
# pure parser
# --------------------------------------------------------------------------- #
def parse_message(msg: dict) -> AisPosition | AisStatic | None:
    if not isinstance(msg, dict):
        return None
    mtype = msg.get("MessageType")
    meta = msg.get("MetaData") or {}
    body = (msg.get("Message") or {}).get(mtype) or {}
    mmsi = meta.get("MMSI") or body.get("UserID") or meta.get("MMSI_String")
    try:
        mmsi = int(mmsi)
    except (TypeError, ValueError):
        return None

    if mtype == "PositionReport":
        lat, lon = body.get("Latitude"), body.get("Longitude")
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return None
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            return None
        return AisPosition(
            mmsi=mmsi, ts=_meta_ts(meta), lat=lat, lon=lon,
            sog_kn=_sog(body.get("Sog")), cog_deg=_cog(body.get("Cog")),
            heading_deg=_heading(body.get("TrueHeading")),
            nav_status=_NAV_STATUS.get(body.get("NavigationalStatus")),
        )

    if mtype == "ShipStaticData":
        dim = body.get("Dimension") or {}
        loa = (dim.get("A") or 0) + (dim.get("B") or 0)
        beam = (dim.get("C") or 0) + (dim.get("D") or 0)
        return AisStatic(
            mmsi=mmsi,
            name=_clean(body.get("Name")) or _clean(meta.get("ShipName")),
            imo=body.get("ImoNumber") or None,
            ship_type=body.get("Type") if body.get("Type") is not None else body.get("ShipType"),
            destination=_clean(body.get("Destination")),
            eta_raw=_eta(body.get("Eta")),
            draft_m=_f(body.get("MaximumStaticDraught")) or None,
            loa_m=float(loa) or None,
            beam_m=float(beam) or None,
        )
    return None


# --------------------------------------------------------------------------- #
# sampler (best-effort I/O)
# --------------------------------------------------------------------------- #
async def _sample_async(seconds: int, bboxes: list, api_key: str) -> tuple[list, list]:
    import websockets

    positions: dict[int, AisPosition] = {}
    statics: dict[int, AisStatic] = {}
    sub = {
        "APIKey": api_key,
        "BoundingBoxes": bboxes,
        "FilterMessageTypes": _WANT_TYPES,
    }
    deadline = time.monotonic() + seconds
    async with websockets.connect(
        AISSTREAM_URL, ping_interval=20, ping_timeout=20, close_timeout=5, max_size=2**23
    ) as ws:
        await ws.send(json.dumps(sub))
        while time.monotonic() < deadline:
            timeout = max(1.0, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            except TimeoutError:
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("error"):
                log.warning("aisstream error frame: %s", str(msg.get("error"))[:200])
                break
            parsed = parse_message(msg)
            if isinstance(parsed, AisPosition):
                positions[parsed.mmsi] = parsed
            elif isinstance(parsed, AisStatic):
                statics[parsed.mmsi] = parsed
    return list(positions.values()), list(statics.values())


def sample(seconds: int | None = None, bboxes: list | None = None) -> dict:
    """Collect the latest position + static frame per MMSI over a short window.

    Returns ``{"ok": bool, "reason": str, "positions": [AisPosition], "statics": [AisStatic]}``.
    Never raises: any failure (no key, missing lib, socket error, timeout) yields
    ``ok=False`` with empty lists so the worker run continues.
    """
    api_key = os.getenv("AISSTREAM_API_KEY", "").strip()
    if not api_key:
        log.warning("AISSTREAM_API_KEY not set -- skipping AIS sample")
        return {"ok": False, "reason": "no api key", "positions": [], "statics": []}
    try:
        import websockets  # noqa: F401
    except ModuleNotFoundError:
        log.warning("websockets not installed -- skipping AIS sample")
        return {"ok": False, "reason": "websockets missing", "positions": [], "statics": []}

    seconds = seconds or int(os.getenv("AIS_SAMPLE_SECONDS", str(_DEFAULT_SECONDS)))
    bboxes = bboxes or _GLOBAL_BBOX
    try:
        pos, stat = asyncio.run(_sample_async(seconds, bboxes, api_key))
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("AIS sample failed: %s", str(exc)[:200])
        return {"ok": False, "reason": str(exc)[:200], "positions": [], "statics": []}

    log.info("AIS sample: %d positions, %d static frames over %ds", len(pos), len(stat), seconds)
    return {"ok": True, "reason": "", "positions": pos, "statics": stat}

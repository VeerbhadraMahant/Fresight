"""Spherical dead-reckoning + nearest-port lookup -- pure functions, no I/O.

Used to (a) project a vessel forward along its last course/speed when AIS goes
quiet, and (b) decide whether a fix is "in port" for voyage inference.
"""

from __future__ import annotations

import math

from ..geo.searoute import haversine_nm  # re-exported for callers

__all__ = ["bearing_deg", "dead_reckon", "haversine_nm", "nearest_port"]

_EARTH_NM = 3440.065


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2, degrees [0, 360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def dead_reckon(
    lat: float, lon: float, sog_kn: float | None, cog_deg: float | None, minutes: float
) -> tuple[float, float]:
    """Advance ``(lat, lon)`` by ``minutes`` at ``sog_kn`` knots on heading ``cog_deg``.

    Returns the input position unchanged when speed/course are missing or the
    vessel is effectively stopped (< 0.3 kn).
    """
    if not sog_kn or sog_kn < 0.3 or cog_deg is None or minutes <= 0:
        return round(lat, 5), round(lon, 5)
    dist_nm = sog_kn * (minutes / 60.0)
    dr = dist_nm / _EARTH_NM
    brg = math.radians(cog_deg % 360.0)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(
        min(1.0, max(-1.0, math.sin(p1) * math.cos(dr) + math.cos(p1) * math.sin(dr) * math.cos(brg)))
    )
    l2 = l1 + math.atan2(
        math.sin(brg) * math.sin(dr) * math.cos(p1),
        math.cos(dr) - math.sin(p1) * math.sin(p2),
    )
    lat2 = math.degrees(p2)
    lon2 = (math.degrees(l2) + 540.0) % 360.0 - 180.0
    return round(lat2, 5), round(lon2, 5)


def nearest_port(lat: float, lon: float, max_nm: float | None = None):
    """Nearest port from the registry as ``(ResolvedPort | None, distance_nm)``.

    With ``max_nm`` set, returns ``(None, distance)`` when the closest port is
    beyond that radius -- used to tell "at a berth" from "at sea".
    """
    from ..geo.ports import REGISTRY

    p = REGISTRY.nearest(lat, lon)
    d = haversine_nm(lat, lon, p.lat, p.lon)
    if max_nm is not None and d > max_nm:
        return None, round(d, 1)
    return p, round(d, 1)

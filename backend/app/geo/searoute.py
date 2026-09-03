"""Sea-route distance + geometry between any two ports.

``sea_route(origin, dest)`` returns a land-avoiding distance (nm) and a polyline
(``[[lon, lat], ...]``, GeoJSON order) by running Dijkstra over the maritime
waypoint graph in ``_searoute_graph``. Ports attach to the graph at their
basin's gateway node; ports in the same basin route by great circle.

Results are cached in the ``lane_geometry`` table when a database is configured,
otherwise in-process.
"""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import pairwise

from ._searoute_graph import BASIN_GATEWAY, EDGES, NODES

log = logging.getLogger("freightsight.searoute")

EARTH_NM = 3440.065  # nautical miles


# --------------------------------------------------------------------------- #
# spherical geometry
# --------------------------------------------------------------------------- #
def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_NM * 2 * math.asin(min(1.0, math.sqrt(a)))


def great_circle_points(
    lat1: float, lon1: float, lat2: float, lon2: float, seg_nm: float = 400.0
) -> list[list[float]]:
    """Interpolated [lon, lat] points along the great circle (inclusive of ends)."""
    d = haversine_nm(lat1, lon1, lat2, lon2)
    n = max(1, int(d / seg_nm))
    if n == 1:
        return [[lon1, lat1], [lon2, lat2]]
    p1, l1 = math.radians(lat1), math.radians(lon1)
    p2, l2 = math.radians(lat2), math.radians(lon2)
    ang = d / EARTH_NM
    sin_ang = math.sin(ang) or 1e-9
    out: list[list[float]] = []
    for i in range(n + 1):
        f = i / n
        a = math.sin((1 - f) * ang) / sin_ang
        b = math.sin(f * ang) / sin_ang
        x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
        y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
        z = a * math.sin(p1) + b * math.sin(p2)
        lat = math.degrees(math.atan2(z, math.hypot(x, y)))
        lon = math.degrees(math.atan2(y, x))
        out.append([round(lon, 3), round(lat, 3)])
    return out


# --------------------------------------------------------------------------- #
# graph
# --------------------------------------------------------------------------- #
def _build_adjacency() -> dict[str, list[tuple[str, float]]]:
    adj: dict[str, list[tuple[str, float]]] = {n: [] for n in NODES}
    seen: set[frozenset[str]] = set()
    for a, b in EDGES:
        if a not in NODES or b not in NODES:
            raise KeyError(f"sea-route edge references unknown node: {a!r}-{b!r}")
        key = frozenset((a, b))
        if key in seen or a == b:
            continue
        seen.add(key)
        la, loa = NODES[a]
        lb, lob = NODES[b]
        w = haversine_nm(la, loa, lb, lob)
        adj[a].append((b, w))
        adj[b].append((a, w))
    return adj


_ADJ = _build_adjacency()


def _dijkstra(src: str, dst: str) -> tuple[float, list[str]]:
    dist = {src: 0.0}
    prev: dict[str, str] = {}
    pq: list[tuple[float, str]] = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > dist.get(u, math.inf):
            continue
        for v, w in _ADJ[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in dist:
        raise RuntimeError(f"no sea-route graph path {src} -> {dst}")
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return dist[dst], list(reversed(path))


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
@dataclass
class SeaRoute:
    distance_nm: float
    via: list[str]
    geometry: list[list[float]] = field(default_factory=list)  # [[lon, lat], ...]
    method: str = "waypoint-graph-v1"

    def as_dict(self) -> dict:
        return {
            "distance_nm": round(self.distance_nm),
            "via": self.via,
            "geometry": self.geometry,
            "method": self.method,
        }


def _gateway(basin: str | None) -> str | None:
    if not basin:
        return None
    return BASIN_GATEWAY.get(basin.upper())


@lru_cache(maxsize=4096)
def _route_cached(
    o_lat: float, o_lon: float, o_basin: str | None,
    d_lat: float, d_lon: float, d_basin: str | None,
) -> SeaRoute:
    og, dg = _gateway(o_basin), _gateway(d_basin)

    # same basin (or unknown) and close -> straight great circle
    if og is None or dg is None or (og == dg):
        dist = haversine_nm(o_lat, o_lon, d_lat, d_lon)
        return SeaRoute(dist, ["origin", "destination"],
                        great_circle_points(o_lat, o_lon, d_lat, d_lon),
                        method="great-circle")

    leg_in = haversine_nm(o_lat, o_lon, *NODES[og])
    graph_nm, node_path = _dijkstra(og, dg)
    leg_out = haversine_nm(*NODES[dg], d_lat, d_lon)
    total = leg_in + graph_nm + leg_out

    geom: list[list[float]] = []
    chain = [(o_lat, o_lon)] + [NODES[n] for n in node_path] + [(d_lat, d_lon)]
    for (a_lat, a_lon), (b_lat, b_lon) in pairwise(chain):
        seg = great_circle_points(a_lat, a_lon, b_lat, b_lon)
        geom.extend(seg if not geom else seg[1:])

    return SeaRoute(total, ["origin", *node_path, "destination"], geom)


def sea_route(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
    origin_basin: str | None = None, dest_basin: str | None = None,
) -> SeaRoute:
    return _route_cached(
        round(origin_lat, 4), round(origin_lon, 4), (origin_basin or None),
        round(dest_lat, 4), round(dest_lon, 4), (dest_basin or None),
    )


def sea_distance_nm(
    origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float,
    origin_basin: str | None = None, dest_basin: str | None = None,
) -> float:
    return sea_route(origin_lat, origin_lon, dest_lat, dest_lon,
                     origin_basin, dest_basin).distance_nm


def graph_stats() -> dict:
    return {"nodes": len(NODES), "edges": sum(len(v) for v in _ADJ.values()) // 2,
            "basins": len(BASIN_GATEWAY)}

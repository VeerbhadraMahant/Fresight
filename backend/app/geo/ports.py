"""Global port registry + resolver.

Resolves any of: canonical code, UN/LOCODE, WPI number, a legacy curated code
(``AUHPT``), a free-text name, or a ``"lat,lon"`` string -> a :class:`ResolvedPort`.

Source of truth, in order:
  1. the ``ports`` table, when ``DATABASE_URL`` is configured and seeded;
  2. otherwise the bundled ``app/data/ports_global.csv`` (curated global set)
     overlaid with the 18 richly-specified legacy ports from ``reference_data``.

Everything downstream (sea-route, lane economics, the future map) goes through
this module so the two backing stores are interchangeable.
"""

from __future__ import annotations

import csv
import logging
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .. import reference_data as ref
from ..db import DB_ENABLED

log = logging.getLogger("freightsight.ports")

_CSV = Path(__file__).resolve().parent.parent / "data" / "ports_global.csv"

_SIZE_LOA = {"Large": (366.0, 65.0), "Medium": (300.0, 50.0), "Small": (230.0, 40.0)}
_SIZE_TPH = {"Large": 1400.0, "Medium": 900.0, "Small": 500.0}


def _norm(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum() or ch == " ").strip()


def _dwt_from_draft(draft: float) -> int:
    return int(min(420_000, max(28_000, (draft / 14.0) ** 3.1 * 82_000)))


@dataclass
class ResolvedPort:
    code: str
    name: str
    lat: float
    lon: float
    country: str | None = None
    country_name: str | None = None
    basin: str | None = None
    water_body: str | None = None
    region: str | None = None
    role: str = "both"
    unlocode: str | None = None
    wpi_number: int | None = None
    max_draft_m: float = 14.0
    max_loa_m: float = 300.0
    max_beam_m: float = 50.0
    max_dwt: int = 85_000
    berth_handling_tph: float = 900.0
    congestion_base_days: float = 2.0
    harbor_size: str | None = None
    transload: bool = False
    curated: bool = False
    source: str | None = None
    aliases: list[str] = field(default_factory=list)

    @property
    def handling_tpd(self) -> float:
        return self.berth_handling_tph * 24.0

    def to_public(self) -> dict:
        return {
            "code": self.code, "name": self.name, "country": self.country,
            "country_name": self.country_name, "basin": self.basin,
            "water_body": self.water_body, "region": self.region, "role": self.role,
            "unlocode": self.unlocode, "lat": round(self.lat, 4), "lon": round(self.lon, 4),
            "max_draft_m": round(self.max_draft_m, 1), "max_loa_m": round(self.max_loa_m),
            "max_beam_m": round(self.max_beam_m, 1), "max_dwt": self.max_dwt,
            "handling_tpd": round(self.handling_tpd), "harbor_size": self.harbor_size,
            "transload": self.transload, "curated": self.curated, "source": self.source,
        }


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #
def _from_curated(p: ref.Port) -> ResolvedPort:
    return ResolvedPort(
        code=p.code, name=p.name, lat=p.lat, lon=p.lon, country=None,
        country_name=p.country, basin=_BASIN_FOR_REGION.get(p.region), region=p.region,
        role=p.role, max_draft_m=p.max_draft_m, max_loa_m=p.max_loa_m,
        max_beam_m=p.max_beam_m, max_dwt=p.max_dwt, berth_handling_tph=p.berth_handling_tph,
        congestion_base_days=p.congestion_base_days, transload=p.transload,
        curated=True, source=p.source or "reference_data",
    )


_BASIN_FOR_REGION = {
    "Australia": "AUS_EAST", "USA": "US_EAST", "Mozambique": "EAST_AFRICA",
    "Indonesia": "SE_ASIA", "Russia": "BALTIC", "India-EastCoast": "BAY_OF_BENGAL",
}


def _from_csv_row(r: dict) -> ResolvedPort:
    draft = float(r["max_draft_m"])
    size = (r.get("harbor_size") or "Medium").strip() or "Medium"
    loa, beam = _SIZE_LOA.get(size, _SIZE_LOA["Medium"])
    return ResolvedPort(
        code=r["code"].strip(),
        name=r["name"].strip(),
        lat=float(r["lat"]), lon=float(r["lon"]),
        country=(r.get("country") or "").strip() or None,
        country_name=(r.get("country_name") or "").strip() or None,
        basin=(r.get("basin") or "").strip() or None,
        water_body=(r.get("water_body") or "").strip() or None,
        role=(r.get("role") or "both").strip() or "both",
        unlocode=(r.get("unlocode") or "").strip() or None,
        max_draft_m=draft, max_loa_m=loa, max_beam_m=beam,
        max_dwt=_dwt_from_draft(draft),
        berth_handling_tph=_SIZE_TPH.get(size, 900.0),
        congestion_base_days=2.0, harbor_size=size,
        source=(r.get("source") or "curated-v1").strip(),
    )


def _from_db_row(row) -> ResolvedPort:
    m = row._mapping
    return ResolvedPort(
        code=m["code"], name=m["name"], lat=m["lat"], lon=m["lon"],
        country=m["country"], country_name=m["country_name"], basin=m["basin"],
        water_body=m["water_body"], region=m["region"], role=m["role"] or "both",
        unlocode=m["unlocode"], wpi_number=m["wpi_number"],
        max_draft_m=m["max_draft_m"] or 14.0,
        max_loa_m=m["max_loa_m"] or 300.0, max_beam_m=m["max_beam_m"] or 50.0,
        max_dwt=m["max_dwt"] or 85_000,
        berth_handling_tph=m["berth_handling_tph"] or 900.0,
        congestion_base_days=m["congestion_base_days"] or 2.0,
        harbor_size=m["harbor_size"], transload=bool(m["transload"]),
        curated=bool(m["curated"]), source=m["source"],
    )


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
class _Registry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_code: dict[str, ResolvedPort] = {}
        self._index: dict[str, str] = {}          # alias (upper) -> code
        self._name_index: list[tuple[str, str]] = []  # (name_norm, code)
        self.backend: str = "unloaded"
        self._loaded = False

    # -- loading -------------------------------------------------------- #
    def _load_bundled(self) -> dict[str, ResolvedPort]:
        ports: dict[str, ResolvedPort] = {}
        with _CSV.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                p = _from_csv_row(row)
                ports[p.code] = p
        # overlay the richly-specified legacy ports (they win on shared codes)
        for p in ref.PORTS.values():
            ports[p.code] = _from_curated(p)
        return ports

    def _load_db(self) -> dict[str, ResolvedPort] | None:
        from sqlalchemy import text

        from ..db import engine
        try:
            with engine().connect() as c:
                rows = c.execute(text("SELECT * FROM ports")).fetchall()
        except Exception as exc:  # table missing / not reachable
            log.info("ports table unavailable (%s) - using bundled CSV", str(exc)[:120])
            return None
        if not rows:
            return None
        return {r._mapping["code"]: _from_db_row(r) for r in rows}

    def _ensure(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            ports: dict[str, ResolvedPort] | None = None
            if DB_ENABLED:
                ports = self._load_db()
                if ports:
                    self.backend = "database"
            if ports is None:
                ports = self._load_bundled()
                self.backend = "bundled-csv"
            self._install(ports)
            self._loaded = True
            log.info("port registry: %d ports (%s)", len(ports), self.backend)

    def _install(self, ports: dict[str, ResolvedPort]) -> None:
        self._by_code = ports
        idx: dict[str, str] = {}
        names: list[tuple[str, str]] = []
        for code, p in ports.items():
            idx[code.upper()] = code
            if p.unlocode:
                idx.setdefault(p.unlocode.upper(), code)
            if p.wpi_number is not None:
                idx.setdefault(str(p.wpi_number), code)
            for a in p.aliases:
                idx.setdefault(a.upper(), code)
            names.append((_norm(p.name), code))
        self._index = idx
        self._name_index = names

    def refresh(self) -> None:
        with self._lock:
            self._loaded = False
        self._ensure()

    # -- queries ------------------------------------------------------- #
    def all(self) -> list[ResolvedPort]:
        self._ensure()
        return list(self._by_code.values())

    def count(self) -> int:
        self._ensure()
        return len(self._by_code)

    def get(self, ident: str) -> ResolvedPort | None:
        self._ensure()
        if ident is None:
            return None
        key = str(ident).strip()
        if not key:
            return None
        hit = self._index.get(key.upper())
        if hit:
            return self._by_code[hit]
        if "," in key:  # "lat,lon"
            try:
                lat_s, lon_s = key.split(",", 1)
                return self.nearest(float(lat_s), float(lon_s))
            except ValueError:
                return None
        # exact name match
        n = _norm(key)
        for name_norm, code in self._name_index:
            if name_norm == n:
                return self._by_code[code]
        return None

    def search(self, q: str, limit: int = 20) -> list[ResolvedPort]:
        self._ensure()
        n = _norm(q or "")
        if not n:
            return []
        scored: list[tuple[int, str]] = []
        for name_norm, code in self._name_index:
            if name_norm == n:
                scored.append((0, code))
            elif name_norm.startswith(n):
                scored.append((1, code))
            elif n in name_norm:
                scored.append((2, code))
        if q.strip().upper() in self._index:
            scored.append((0, self._index[q.strip().upper()]))
        seen: set[str] = set()
        out: list[ResolvedPort] = []
        for _, code in sorted(scored, key=lambda t: (t[0], self._by_code[t[1]].name)):
            if code in seen:
                continue
            seen.add(code)
            out.append(self._by_code[code])
            if len(out) >= limit:
                break
        return out

    def nearest(self, lat: float, lon: float) -> ResolvedPort:
        self._ensure()
        best: ResolvedPort | None = None
        best_d = math.inf
        for p in self._by_code.values():
            d = (p.lat - lat) ** 2 + (p.lon - lon) ** 2
            if d < best_d:
                best_d, best = d, p
        assert best is not None
        return best


REGISTRY = _Registry()


def load_bundled() -> dict[str, ResolvedPort]:
    """The merged CSV + curated port set, regardless of DB availability (for seeding)."""
    return _Registry()._load_bundled()


def get(ident: str) -> ResolvedPort | None:
    return REGISTRY.get(ident)


def require(ident: str) -> ResolvedPort:
    p = REGISTRY.get(ident)
    if p is None:
        raise KeyError(f"unknown port: {ident!r}")
    return p


def search(q: str, limit: int = 20) -> list[ResolvedPort]:
    return REGISTRY.search(q, limit)


def all_ports() -> list[ResolvedPort]:
    return REGISTRY.all()


def count() -> int:
    return REGISTRY.count()

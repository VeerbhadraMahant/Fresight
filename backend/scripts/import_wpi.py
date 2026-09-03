"""Import the real NGA World Port Index (Pub 150) into the ``ports`` table.

The bundled global set (`load_ports.py`) is a curated ~130-port list. Drop in the
authoritative NGA file for full ~3,700-port coverage:

    1. Download "World Port Index (Pub 150)" CSV from
       https://msi.nga.mil/Publications/WPI   (public domain, US Gov)
    2. DATABASE_URL=postgresql://...  python backend/scripts/import_wpi.py path/to/UpdatedPub150.csv

Rows are upserted by a synthetic code ``WPI:<number>`` (or the UN/LOCODE when
present). Rows whose code collides with a curated port are skipped -- the
hand-verified constraint data wins.

Handled column names (NGA has renamed these across releases; unknown columns are
ignored):
    World Port Index Number | Index No.
    Main Port Name | Port Name
    UN/LOCODE
    Country Code | Country
    Latitude / Longitude   (decimal degrees)
    Harbor Size
    Channel Depth (m) | Maximum Vessel Draft (m) | Cargo Pier Depth (m)
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import DB_ENABLED, session_scope
from app.db.models import IngestRun, Port

_ALIASES = {
    "wpi_number": ["World Port Index Number", "Index No.", "Index Number", "PORT_INDEX"],
    "name": ["Main Port Name", "Port Name", "PORT_NAME", "portname"],
    "unlocode": ["UN/LOCODE", "UNLOCODE", "unlocode"],
    "country": ["Country Code", "Country", "COUNTRY"],
    "lat": ["Latitude", "LATITUDE", "lat", "Y"],
    "lon": ["Longitude", "LONGITUDE", "lon", "X"],
    "harbor_size": ["Harbor Size", "HARBORSIZE", "Harbor Size Code"],
    "water_body": ["World Water Body", "Ocean or Sea", "WATER_BODY"],
    "depth": ["Maximum Vessel Draft (m)", "Channel Depth (m)", "Cargo Pier Depth (m)",
              "Maximum Vessel Draft", "Channel Depth"],
}

_SIZE_DRAFT = {"V": 6.0, "S": 9.0, "M": 12.5, "L": 17.0,
               "Very Small": 6.0, "Small": 9.0, "Medium": 12.5, "Large": 17.0}


def _pick(row: dict, key: str) -> str | None:
    for name in _ALIASES[key]:
        if name in row and str(row[name]).strip():
            return str(row[name]).strip()
    return None


def _draft(row: dict) -> float:
    raw = _pick(row, "depth")
    if raw:
        try:
            v = float(raw.split()[0].replace(",", ""))
            if 2.0 <= v <= 40.0:
                return v
        except ValueError:
            pass
    size = _pick(row, "harbor_size") or ""
    return _SIZE_DRAFT.get(size, _SIZE_DRAFT.get(size[:1].upper(), 11.0))


def main() -> None:
    if not DB_ENABLED:
        raise SystemExit("DATABASE_URL is not set.")
    if len(sys.argv) < 2:
        raise SystemExit("usage: python backend/scripts/import_wpi.py <UpdatedPub150.csv>")

    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"file not found: {path}")

    started = datetime.now(UTC)
    inserted = updated = skipped = 0

    with path.open(newline="", encoding="utf-8-sig") as fh, session_scope() as s:
        curated_codes = {c for (c,) in s.execute(select(Port.code).where(Port.curated.is_(True)))}
        for raw in csv.DictReader(fh):
            name = _pick(raw, "name")
            lat, lon = _pick(raw, "lat"), _pick(raw, "lon")
            if not name or lat is None or lon is None:
                continue
            try:
                latf, lonf = float(lat), float(lon)
            except ValueError:
                continue
            wpi = _pick(raw, "wpi_number")
            unloc = _pick(raw, "unlocode")
            code = (unloc.upper() if unloc and len(unloc) == 5 else f"WPI:{wpi or name[:12]}")
            if code in curated_codes:
                skipped += 1
                continue

            draft = _draft(raw)
            size = _pick(raw, "harbor_size")
            values = {
                "code": code, "wpi_number": int(wpi) if wpi and wpi.isdigit() else None,
                "unlocode": unloc, "name": name, "name_norm": name.upper().strip(),
                "country": (_pick(raw, "country") or None), "country_name": None,
                "water_body": _pick(raw, "water_body"), "region": None, "basin": None,
                "role": "both", "lat": latf, "lon": lonf,
                "max_draft_m": draft, "max_loa_m": 366.0, "max_beam_m": 65.0,
                "max_dwt": int(min(420_000, max(28_000, (draft / 14.0) ** 3.1 * 82_000))),
                "berth_handling_tph": 1000.0, "congestion_base_days": 2.0,
                "harbor_size": size, "transload": False, "curated": False,
                "source": "NGA World Port Index (Pub 150)",
            }
            existing = s.scalar(select(Port).where(Port.code == code))
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                s.add(Port(**values))
                inserted += 1

        s.add(IngestRun(feed="ports", started_at=started, finished_at=datetime.now(UTC),
                        ok=True, rows=inserted + updated,
                        detail={"source": "wpi", "inserted": inserted,
                                "updated": updated, "skipped_curated": skipped}))

    print(f"WPI import: +{inserted} new, {updated} updated, {skipped} curated-skipped")


if __name__ == "__main__":
    main()

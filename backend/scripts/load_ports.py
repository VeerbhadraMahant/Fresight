"""Seed / refresh the ``ports`` table from the bundled global port set.

    DATABASE_URL=postgresql://...  python backend/scripts/load_ports.py

Idempotent: upserts by ``code``. Curated (legacy) ports keep their richer
constraint fields. Records an ``ingest_runs`` row. Safe to re-run any time and
after ``import_wpi.py`` (WPI rows that share a code are overwritten by the
curated values, which is intended).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import DB_ENABLED, session_scope
from app.db.models import IngestRun, Port
from app.geo.ports import ResolvedPort, load_bundled


def _row(p: ResolvedPort) -> dict:
    return {
        "code": p.code, "unlocode": p.unlocode, "wpi_number": p.wpi_number,
        "name": p.name, "name_norm": p.name.upper().strip(),
        "country": p.country, "country_name": p.country_name,
        "water_body": p.water_body, "region": p.region, "basin": p.basin,
        "role": p.role, "lat": p.lat, "lon": p.lon,
        "max_draft_m": p.max_draft_m, "max_loa_m": p.max_loa_m, "max_beam_m": p.max_beam_m,
        "max_dwt": p.max_dwt, "berth_handling_tph": p.berth_handling_tph,
        "congestion_base_days": p.congestion_base_days, "harbor_size": p.harbor_size,
        "transload": p.transload, "curated": p.curated, "source": p.source,
    }


def main() -> None:
    if not DB_ENABLED:
        raise SystemExit("DATABASE_URL is not set -- nothing to seed.")

    rows = [_row(p) for p in load_bundled().values()]
    started = datetime.now(UTC)
    written = 0

    with session_scope() as s:
        dialect = s.bind.dialect.name
        for r in rows:
            if dialect == "postgresql":
                stmt = pg_insert(Port).values(**r)
                update = {k: stmt.excluded[k] for k in r if k not in ("code",)}
                stmt = stmt.on_conflict_do_update(index_elements=["code"], set_=update)
                s.execute(stmt)
            else:
                existing = s.scalar(select(Port).where(Port.code == r["code"]))
                if existing:
                    for k, v in r.items():
                        setattr(existing, k, v)
                else:
                    s.add(Port(**r))
            written += 1
        s.add(IngestRun(feed="ports", started_at=started, finished_at=datetime.now(UTC),
                        ok=True, rows=written, detail={"source": "bundled"}))

    print(f"ports upserted: {written}")


if __name__ == "__main__":
    main()

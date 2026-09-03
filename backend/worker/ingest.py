"""The self-updating pipeline -- one pass.

    DATABASE_URL=postgresql://...  python -m worker.ingest

Steps (each best-effort, each writes an ``ingest_runs`` row):
  1. fetch the external feeds (BDRY, Brent, IMF PortWatch, Open-Meteo) and stash
     the bundle in ``feed_snapshots`` -- this is what the API seeds itself from;
  2. rebuild the hybrid market dataset;
  3. append the latest modelled rate per lane x vessel to ``freight_rates``
     (history accrues -> the forecaster eventually trains on real observations);
  4. snapshot every active forecast to ``rate_forecasts`` (walk-forward skill);
  5. upsert the risk scan into ``alerts`` with open/expired lifecycle.

Env:
  FREIGHTSIGHT_LIVE_REFRESH_BUDGET   seconds for the live feed fetch (default 12; set ~120 in CI)
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import reference_data as ref
from app.datasources import load_real_data, snapshot_dict
from app.db import DB_ENABLED, session_scope
from app.db.models import Alert, FeedSnapshot, FreightRate, IngestRun, RateForecast
from app.forecasting import forecast as run_forecast
from app.idle_risk import scan_risks
from app.synthetic import generate

log = logging.getLogger("freightsight.worker")


def _as_date(s: str | None) -> date | None:
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _upsert(model, rows: list[dict], keys: list[str]) -> int:
    if not rows:
        return 0
    with session_scope() as s:
        if s.bind.dialect.name == "postgresql":
            stmt = pg_insert(model).values(rows)
            update = {
                c.name: stmt.excluded[c.name]
                for c in model.__table__.columns
                if c.name not in keys and c.name != "id"
            }
            s.execute(stmt.on_conflict_do_update(index_elements=keys, set_=update))
        else:
            for r in rows:
                q = select(model)
                for k in keys:
                    q = q.where(getattr(model, k) == r[k])
                existing = s.scalars(q).first()
                if existing:
                    for k, v in r.items():
                        setattr(existing, k, v)
                else:
                    s.add(model(**r))
    return len(rows)


# --------------------------------------------------------------------------- #
def _ingest_realdata() -> tuple[object, dict]:
    t0 = datetime.now(UTC)
    ok, err, real = True, None, None
    try:
        # prefer_db=False: the worker must hit the network, not read its own last row
        real = load_real_data(live_refresh=True, prefer_db=False)
    except Exception as exc:  # pragma: no cover - network dependent
        ok, err = False, str(exc)[:400]
    detail = {
        "sources": dict(real.sources) if real is not None else {},
        "as_of": real.snapshot_date if real is not None else None,
    }
    with session_scope() as s:
        s.add(FeedSnapshot(
            feed="realdata", fetched_at=t0,
            as_of=_as_date(detail["as_of"]), ok=ok,
            payload=snapshot_dict(real) if real is not None else {}, meta=detail,
        ))
        s.add(IngestRun(
            feed="realdata", started_at=t0, finished_at=datetime.now(UTC),
            ok=ok, rows=len(detail["sources"]), detail=detail, error=err,
        ))
    return real, detail


def _persist_rates(md, mode: str) -> dict:
    ts = md.freight.index[-1].date()
    latest = md.freight.iloc[-1]
    rows = [
        {"route_id": rid, "vessel": vessel, "ts": ts,
         "rate_usd_t": round(float(val), 3), "source": mode}
        for (rid, vessel), val in latest.items() if val == val  # skip NaN
    ]
    written = _upsert(FreightRate, rows, ["route_id", "vessel", "ts"])
    return {"written": written, "as_of": str(ts)}


def _persist_forecasts(md) -> dict:
    run_ts = datetime.now(UTC)
    out: list[RateForecast] = []
    for rid in ref.ROUTES:
        for vessel in ref.VESSEL_ORDER:
            if (rid, vessel) not in md.freight.columns:
                continue
            try:
                f = run_forecast(md, rid, vessel, horizon_days=100)
            except Exception:  # pragma: no cover - a lane with too little history
                continue
            mo = (f.get("monthly") or [{}])[-1]
            bt = f.get("backtest", {})
            er = f.get("expected_rate", {})
            out.append(RateForecast(
                run_ts=run_ts, route_id=rid, vessel=vessel,
                latest_rate=f.get("latest_rate"),
                exp_30d=er.get("next_30d"), exp_60d=er.get("next_60d"), exp_90d=er.get("next_90d"),
                lo_90d=mo.get("lo"), hi_90d=mo.get("hi"),
                model=f.get("model"),
                mape=bt.get("ensemble", {}).get("mape"),
                skill_vs_rw_pct=bt.get("skill_vs_random_walk_pct"),
            ))
    with session_scope() as s:
        s.add_all(out)
    return {"written": len(out), "run_ts": run_ts.isoformat()}


def _persist_alerts(md) -> dict:
    now = datetime.now(UTC)
    scan = scan_risks(md, max_alerts=60)
    seen = [a["id"] for a in scan["alerts"]]
    expired = 0
    with session_scope() as s:
        for a in scan["alerts"]:
            row = s.get(Alert, a["id"])
            fields = {
                "category": a["category"], "severity": a["severity"], "scope": a["scope"],
                "message": a["message"], "recommended_action": a.get("recommended_action"),
                "metrics": a.get("metrics"), "status": "open",
                "last_seen_at": now, "expired_at": None,
            }
            if row:
                for k, v in fields.items():
                    setattr(row, k, v)
            else:
                s.add(Alert(id=a["id"], opened_at=now, **fields))
        stale = s.scalars(
            select(Alert).where(Alert.status == "open", Alert.id.not_in(seen or ["__none__"]))
        ).all()
        for row in stale:
            row.status, row.expired_at = "expired", now
        expired = len(stale)
    return {"open": len(seen), "expired": expired}


# --------------------------------------------------------------------------- #
def run() -> dict:
    if not DB_ENABLED:
        # No database configured yet -> nothing to persist. Exit 0 so the
        # scheduled workflow isn't a permanent red X before DATABASE_URL is set.
        log.warning("DATABASE_URL is not set -- skipping ingest (no database to write to).")
        return {"skipped": "DATABASE_URL not set"}

    started = datetime.now(UTC)
    log.info("ingest starting")

    real, feed_detail = _ingest_realdata()
    md = generate(real=real)
    mode = "hybrid" if (real is not None and real.any_live()) else "synthetic"

    summary = {
        "mode": mode,
        "realdata": feed_detail,
        "freight_rates": _persist_rates(md, mode),
        "forecasts": _persist_forecasts(md),
        "alerts": _persist_alerts(md),
    }

    with session_scope() as s:
        s.add(IngestRun(
            feed="ingest", started_at=started, finished_at=datetime.now(UTC), ok=True,
            rows=summary["freight_rates"]["written"] + summary["forecasts"]["written"],
            detail=summary,
        ))
    log.info("ingest done: %s", summary)
    return summary


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run()
    except SystemExit:
        raise
    except Exception as exc:
        log.exception("ingest failed")
        try:
            with session_scope() as s:
                s.add(IngestRun(feed="ingest", started_at=datetime.now(UTC),
                                finished_at=datetime.now(UTC), ok=False, rows=0,
                                error=str(exc)[:800]))
        except Exception:
            pass
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

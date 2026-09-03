"""System status + the self-updating pipeline's control surface.

  GET  /api/system/health        liveness + real feed freshness (from ingest_runs)
  GET  /api/system/ingest-runs   recent worker runs
  POST /api/internal/refresh     token-guarded: reload the dataset from the DB snapshot
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException

from .. import __version__
from ..db import DB_ENABLED, healthcheck
from ..geo import ports as port_reg
from ..geo.searoute import graph_stats
from ..market_store import STORE

router = APIRouter(prefix="/api", tags=["system"])

STALE_AFTER_MIN = 45.0
_REFRESH_TOKEN = os.getenv("FREIGHTSIGHT_REFRESH_TOKEN", "").strip()


def _feed_freshness() -> dict:
    """Latest successful ingest per feed, with age + a stale flag."""
    if not DB_ENABLED:
        return {}
    try:
        from sqlalchemy import func, select

        from ..db import session_scope
        from ..db.models import IngestRun

        out: dict = {}
        with session_scope() as s:
            latest_ok = (
                select(IngestRun.feed, func.max(IngestRun.finished_at).label("ts"))
                .where(IngestRun.ok.is_(True), IngestRun.finished_at.is_not(None))
                .group_by(IngestRun.feed)
            )
            now = datetime.now(UTC)
            for feed, ts in s.execute(latest_ok):
                age = (now - ts).total_seconds() / 60.0 if ts else None
                out[feed] = {
                    "last_ok_at": ts.isoformat() if ts else None,
                    "age_min": round(age, 1) if age is not None else None,
                    "stale": (age is None) or (age > STALE_AFTER_MIN),
                }
        return out
    except Exception as exc:  # pragma: no cover - db/network dependent
        return {"_error": str(exc)[:200]}


def _history_counts() -> dict:
    if not DB_ENABLED:
        return {}
    try:
        from sqlalchemy import func, select

        from ..db import session_scope
        from ..db.models import Alert, FreightRate, RateForecast

        with session_scope() as s:
            return {
                "freight_rate_points": s.scalar(select(func.count()).select_from(FreightRate)) or 0,
                "forecast_runs": s.scalar(
                    select(func.count(func.distinct(RateForecast.run_ts)))
                ) or 0,
                "open_alerts": s.scalar(
                    select(func.count()).select_from(Alert).where(Alert.status == "open")
                ) or 0,
            }
    except Exception as exc:  # pragma: no cover
        return {"_error": str(exc)[:200]}


@router.get("/system/health", tags=["meta"])
def system_health():
    reg = port_reg.REGISTRY
    prov = STORE.provenance
    feeds = _feed_freshness()
    self_updating = bool(feeds) and not feeds.get("_error")
    return {
        "version": __version__,
        "self_updating": self_updating,
        "database": {"configured": DB_ENABLED, **healthcheck()},
        "ports": {"count": reg.count(), "backend": reg.backend},
        "searoute": graph_stats(),
        "market": {
            "mode": prov.mode,
            "snapshot_date": prov.snapshot_date,
            "refreshing": prov.refreshing,
            "data_sources": prov.data_sources,
        },
        "feeds": feeds,
        "history": _history_counts(),
        "stale_after_min": STALE_AFTER_MIN,
    }


@router.get("/system/ingest-runs", tags=["meta"])
def ingest_runs(limit: int = 20):
    if not DB_ENABLED:
        return {"enabled": False, "runs": []}
    from sqlalchemy import select

    from ..db import session_scope
    from ..db.models import IngestRun

    limit = max(1, min(limit, 100))
    with session_scope() as s:
        rows = s.scalars(
            select(IngestRun).order_by(IngestRun.id.desc()).limit(limit)
        ).all()
        return {
            "enabled": True,
            "runs": [
                {
                    "id": r.id, "feed": r.feed, "ok": r.ok, "rows": r.rows,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "error": r.error,
                    "detail": r.detail,
                }
                for r in rows
            ],
        }


@router.post("/internal/refresh", tags=["meta"])
def internal_refresh(x_refresh_token: str | None = Header(default=None)):
    """Reload the in-memory dataset from the latest DB snapshot the worker wrote.

    Cheap (no outbound HTTP). Meant for the keep-warm cron to call between worker
    runs. Disabled unless FREIGHTSIGHT_REFRESH_TOKEN is set.
    """
    if not _REFRESH_TOKEN:
        raise HTTPException(503, "refresh endpoint disabled (set FREIGHTSIGHT_REFRESH_TOKEN)")
    if x_refresh_token != _REFRESH_TOKEN:
        raise HTTPException(401, "bad or missing X-Refresh-Token")
    as_of = STORE.reload()
    p = STORE.provenance
    return {"reloaded": True, "mode": p.mode, "snapshot_date": as_of,
            "data_sources": p.data_sources}

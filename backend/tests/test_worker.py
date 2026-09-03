"""The self-updating ingest pipeline (worker/ingest.py) + system status endpoints.

The worker runs as a subprocess with its own DATABASE_URL so the test exercises
the real DB code path without fighting import-time env capture in app.db.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

BACKEND = Path(__file__).resolve().parents[1]


def _env(db_path: Path) -> dict:
    return {
        **os.environ,
        "DATABASE_URL": f"sqlite+pysqlite:///{db_path.as_posix()}",
        "FREIGHTSIGHT_SKIP_LIVE_PROBE": "1",
        "FREIGHTSIGHT_DISABLE_REALDATA": "1",  # no network in CI -> synthetic dataset
        "FREIGHTSIGHT_LIVE_REFRESH_BUDGET": "1",
    }


def _run(args: list[str], env: dict):
    return subprocess.run(
        [sys.executable, *args], cwd=BACKEND, env=env,
        capture_output=True, text=True, timeout=300,
    )


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    db = tmp_path_factory.mktemp("worker") / "t.db"
    env = _env(db)
    mig = _run(["-m", "alembic", "upgrade", "head"], env)
    assert mig.returncode == 0, mig.stderr
    run1 = _run(["-m", "worker.ingest"], env)
    assert run1.returncode == 0, run1.stderr + run1.stdout
    return db, env


def _count(db: Path, sql: str) -> int:
    con = sqlite3.connect(db)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def test_migrations_apply_0001_and_0002(seeded_db):
    db, _ = seeded_db
    tables = {
        r[0] for r in sqlite3.connect(db).execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"ports", "freight_rates", "rate_forecasts", "alerts", "feed_snapshots"} <= tables


def test_worker_populates_history(seeded_db):
    db, _ = seeded_db
    assert _count(db, "SELECT count(*) FROM freight_rates") > 20
    assert _count(db, "SELECT count(*) FROM rate_forecasts") > 10
    assert _count(db, "SELECT count(*) FROM feed_snapshots WHERE feed='realdata'") == 1
    assert _count(db, "SELECT count(*) FROM ingest_runs WHERE feed='ingest' AND ok=1") == 1
    # a forecast row carries the model + a MAPE
    row = sqlite3.connect(db).execute(
        "SELECT model, mape, exp_90d FROM rate_forecasts WHERE mape IS NOT NULL LIMIT 1"
    ).fetchone()
    assert row and row[0] and 0 < row[1] < 60 and row[2] > 0


def test_worker_runs_ais_step_and_skips_without_key(seeded_db):
    db, _ = seeded_db
    # the AIS step always records an ingest_runs row; with no AISSTREAM_API_KEY
    # it is a graceful skip (ok=1, rows=0) rather than a failure
    row = sqlite3.connect(db).execute(
        "SELECT ok, rows, detail FROM ingest_runs WHERE feed='ais' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row[0] == 1 and row[1] == 0
    assert "skip" in (row[2] or "").lower() or "api key" in (row[2] or "").lower()


def test_worker_is_idempotent_and_accrues(seeded_db):
    db, env = seeded_db
    before_runs = _count(db, "SELECT count(*) FROM ingest_runs WHERE feed='ingest'")
    before_rates = _count(db, "SELECT count(*) FROM freight_rates")
    run2 = _run(["-m", "worker.ingest"], env)
    assert run2.returncode == 0, run2.stderr
    # same as-of date -> rates upsert in place, not duplicate
    assert _count(db, "SELECT count(*) FROM freight_rates") == before_rates
    # every run appends its own audit row + a fresh forecast snapshot
    assert _count(db, "SELECT count(*) FROM ingest_runs WHERE feed='ingest'") == before_runs + 1
    assert _count(db, "SELECT count(DISTINCT run_ts) FROM rate_forecasts") >= 2


# --------------------------------------------------------------------------- #
# system endpoints in the no-DB configuration (the default for CI + the tests)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_without_db_reports_not_self_updating(client):
    j = client.get("/api/system/health").json()
    assert j["database"]["configured"] is False
    assert j["self_updating"] is False
    assert j["feeds"] == {} and j["history"] == {}
    assert j["ports"]["count"] >= 140


def test_ingest_runs_endpoint_without_db(client):
    j = client.get("/api/system/ingest-runs").json()
    assert j["enabled"] is False and j["runs"] == []


def test_internal_refresh_disabled_without_token(client):
    assert client.post("/api/internal/refresh").status_code == 503


def test_worker_skips_gracefully_without_database_url():
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["FREIGHTSIGHT_SKIP_LIVE_PROBE"] = "1"
    r = _run(["-m", "worker.ingest"], env)
    assert r.returncode == 0, r.stderr
    assert "skipping ingest" in (r.stderr + r.stdout).lower()

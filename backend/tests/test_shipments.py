"""Phase D -- shipment tracking (app/shipments.py + /api/shipments).

Like test_worker, the DB-backed path runs in a subprocess with its own
DATABASE_URL so it exercises real SQL without fighting app.db's import-time env
capture. A second class checks the no-database behaviour in-process.
"""

import os
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
        "FREIGHTSIGHT_DISABLE_REALDATA": "1",
        "FREIGHTSIGHT_SKIP_DOTENV": "1",
    }


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=BACKEND, env=env,
        capture_output=True, text=True, timeout=300,
    )


_DRIVER = r"""
import json
from app.market_store import STORE
from app import shipments as svc
from app.db import session_scope
from app.db.models import Shipment

STORE.build()

created = svc.create({
    "origin_code": "AUHPT", "dest_code": "INPRT", "commodity": "Iron Ore",
    "cargo_t": 160000, "vessel_class": "Capesize", "contract_months": 6,
})
assert created["ref"].startswith("SHP-"), created
assert created["baseline_usd_per_t"] and created["baseline_usd_per_t"] > 0, created

listed = svc.list_all()
assert len(listed) == 1 and listed[0]["ref"] == created["ref"]

detail = svc.get(created["ref"])
assert detail["valuation"]["delivered_usd_per_t"] > 0
assert detail["analysis"]["recommendation"]["vessel"] == "Capesize"
assert isinstance(detail["analysis"]["route_geometry"], list) and detail["analysis"]["route_geometry"]

summary = svc.revalue_all()
assert summary == {"shipments": 1, "valued": 1, "errors": 0}, summary

after = svc.get(created["ref"])
assert len(after["cost_history"]) == 1
pt = after["cost_history"][0]
assert pt["drift_usd_per_t"] is not None  # baseline was captured -> drift computable

patched = svc.update(created["ref"], {"status": "arrived"})
assert patched["status"] == "arrived"
# terminal shipments are not re-valued
assert svc.revalue_all()["shipments"] == 0

assert svc.delete(created["ref"]) is True
assert svc.get(created["ref"]) is None
with session_scope() as s:
    assert s.query(Shipment).count() == 0

print("DRIVER_OK")
"""


@pytest.fixture(scope="module")
def db_env(tmp_path_factory):
    db = tmp_path_factory.mktemp("shipments") / "t.db"
    env = _env(db)
    mig = _run(["-m", "alembic", "upgrade", "head"], env)
    assert mig.returncode == 0, mig.stderr
    return env


def test_shipment_lifecycle_against_db(db_env):
    res = _run(["-c", _DRIVER], db_env)
    assert res.returncode == 0, res.stderr + res.stdout
    assert "DRIVER_OK" in res.stdout


def test_migration_0005_creates_tables(db_env):
    res = _run(
        ["-c", "from sqlalchemy import inspect, create_engine; import os;"
               "e=create_engine(os.environ['DATABASE_URL']);"
               "print(sorted(t for t in inspect(e).get_table_names() if 'shipment' in t))"],
        db_env,
    )
    assert res.returncode == 0, res.stderr
    assert "shipments" in res.stdout and "shipment_costs" in res.stdout


class TestNoDatabase:
    """With no DATABASE_URL the endpoints degrade to a clear disabled state."""

    def test_list_returns_disabled(self):
        with TestClient(app) as c:
            r = c.get("/api/shipments")
        assert r.status_code == 200
        assert r.json() == {"enabled": False,
                            "reason": "no database configured (DATABASE_URL)",
                            "shipments": []}

    def test_create_rejected(self):
        with TestClient(app) as c:
            r = c.post("/api/shipments", json={
                "origin_code": "AUHPT", "dest_code": "INPRT", "cargo_t": 1000,
            })
        assert r.status_code == 503

"""Global geography layer: port resolver, sea-route graph, any-lane economics."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.db.models import Base
from app.geo import ports as reg
from app.geo.searoute import graph_stats, sea_route
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def test_orm_metadata_creates_cleanly_on_sqlite():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    tables = set(inspect(eng).get_table_names())
    assert {"ports", "lane_geometry", "ingest_runs", "vessels", "positions", "voyages"} <= tables


def test_initial_migration_module_is_wellformed():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial_schema.py"
    spec = importlib.util.spec_from_file_location("_mig0001", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.upgrade) and callable(mod.downgrade)
    assert mod.revision == "0001" and mod.down_revision is None


# --------------------------------------------------------------------------- #
# port registry
# --------------------------------------------------------------------------- #
def test_registry_loads_bundled_global_set():
    assert reg.count() >= 140
    assert reg.REGISTRY.backend == "bundled-csv"


@pytest.mark.parametrize("ident", ["NLRTM", "Rotterdam", "rotterdam", "ROTTERDAM"])
def test_resolve_rotterdam_many_ways(ident):
    p = reg.get(ident)
    assert p is not None and p.code == "NLRTM"
    assert 51 < p.lat < 53 and 3 < p.lon < 5


def test_curated_legacy_ports_win_and_keep_rich_fields():
    hp = reg.get("AUHPT")
    assert hp is not None and hp.curated is True
    assert hp.max_draft_m == pytest.approx(17.4, abs=0.01)
    assert hp.handling_tpd > 100_000  # Hay Point is a fast coal terminal


def test_resolve_by_latlon_returns_nearest():
    p = reg.get("13.1,80.3")  # off Chennai / Ennore
    assert p is not None and p.country in ("IN", None)
    assert p.lat == pytest.approx(13.1, abs=2.0)


def test_search_ranks_prefix_first():
    res = reg.search("shang", limit=5)
    assert res and res[0].code == "CNSHG"


# --------------------------------------------------------------------------- #
# sea-route graph
# --------------------------------------------------------------------------- #
def test_graph_is_connected_enough():
    s = graph_stats()
    assert s["nodes"] > 70 and s["edges"] > 80 and s["basins"] >= 28


def _route(o_code, d_code):
    o, d = reg.require(o_code), reg.require(d_code)
    return sea_route(o.lat, o.lon, d.lat, d.lon, o.basin, d.basin)


def test_rotterdam_shanghai_goes_through_suez():
    r = _route("NLRTM", "CNSHG")
    assert any("SUEZ" in v for v in r.via)
    assert 9_000 < r.distance_nm < 14_000
    assert len(r.geometry) > 10


def test_brazil_china_goes_round_the_cape_not_suez():
    r = _route("BRTUB", "CNTAO")
    assert not any("SUEZ" in v for v in r.via)
    assert any("AGULHAS" in v or "CAPE_TOWN" in v for v in r.via)
    assert 10_000 < r.distance_nm < 15_000


def test_us_gulf_to_japan_uses_panama():
    r = _route("USMSY", "JPCHB")
    assert any("PANAMA" in v for v in r.via)


def test_same_basin_route_is_direct_great_circle():
    r = _route("CNQHD", "CNTAO")  # both CHINA_NORTH
    assert r.method == "great-circle"
    assert r.distance_nm < 800


def test_curated_australia_india_lane_is_in_range():
    r = _route("AUHPT", "INPRT")  # curated says ~6300 nm
    assert 4_500 < r.distance_nm < 8_500


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def test_ports_search_endpoint(client):
    j = client.get("/api/reference/ports/search", params={"q": "rotter"}).json()
    assert j["results"] and j["results"][0]["code"] == "NLRTM"


def test_resolve_port_endpoint(client):
    assert client.get("/api/reference/port", params={"ident": "AUHPT"}).json()["curated"] is True
    assert client.get("/api/reference/port", params={"ident": "nope-nope"}).status_code == 404


def test_geo_route_endpoint_returns_geometry(client):
    j = client.get("/api/geo/route", params={"origin": "NLRTM", "destination": "SGSIN"}).json()
    assert j["distance_nm"] > 6_000
    assert isinstance(j["geometry"], list) and len(j["geometry"]) > 5
    assert any("SUEZ" in v for v in j["via"])


def test_geo_lane_endpoint_any_port_pair(client):
    j = client.get("/api/geo/lane", params={
        "origin": "AUPHE", "destination": "CNTAO",
        "commodity": "Iron Ore", "cargo_volume_t": 400_000,
    }).json()
    assert j["calibrated"] is False
    assert len(j["options"]) == 5
    assert j["recommendation"] is not None and j["recommendation"]["feasible"]
    # Port Hedland -> Qingdao is a short Capesize iron-ore haul (real C5 ~ $8-12/t)
    assert 4 < j["recommendation"]["freight_usd_per_t"] < 60
    assert j["recommendation"]["vessel"] in ("Capesize", "Kamsarmax", "Panamax")
    assert j["route"]["distance_nm"] > 3_000
    assert len(j["route"]["geometry"]) > 5


def test_geo_lane_rejects_same_port(client):
    assert client.get("/api/geo/lane", params={"origin": "NLRTM", "destination": "NLRTM"}).status_code == 400


def test_system_health_endpoint(client):
    j = client.get("/api/system/health").json()
    assert j["ports"]["count"] >= 140
    assert j["database"]["configured"] is False
    assert j["searoute"]["nodes"] > 70
    assert j["market"]["mode"] in ("hybrid", "synthetic")

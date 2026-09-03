"""Phase 3 live-monitoring: AIS parsing, dead-reckoning, and the /api/map/*
read layer in the no-database configuration (CI default)."""

import pytest
from fastapi.testclient import TestClient

from app.live.ais import AisPosition, AisStatic, is_dry_bulk, parse_message, sample
from app.live.reckon import bearing_deg, dead_reckon, haversine_nm, nearest_port
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------- #
# dead-reckoning / geometry (pure)
# --------------------------------------------------------------------------- #
def test_dead_reckon_due_east_on_equator():
    # 12 kn for 60 min = 12 nm; at the equator 1' lon ~ 1 nm -> ~0.2 deg east
    lat, lon = dead_reckon(0.0, 0.0, sog_kn=12.0, cog_deg=90.0, minutes=60.0)
    assert abs(lat) < 1e-3
    assert 0.18 < lon < 0.22


def test_dead_reckon_noops_when_stopped_or_courseless():
    assert dead_reckon(10.0, 20.0, sog_kn=0.0, cog_deg=90.0, minutes=120.0) == (10.0, 20.0)
    assert dead_reckon(10.0, 20.0, sog_kn=11.0, cog_deg=None, minutes=120.0) == (10.0, 20.0)


def test_dead_reckon_matches_haversine_distance():
    lat, lon = dead_reckon(35.0, 139.0, sog_kn=15.0, cog_deg=210.0, minutes=180.0)
    # 15 kn * 3 h = 45 nm travelled
    assert 43.0 < haversine_nm(35.0, 139.0, lat, lon) < 47.0


def test_bearing_cardinal():
    assert abs(bearing_deg(0, 0, 0, 1) - 90.0) < 1e-6      # due east
    assert abs(bearing_deg(0, 0, 1, 0) - 0.0) < 1e-6       # due north


def test_nearest_port_hits_and_misses():
    # near Rotterdam (51.95, 4.14) -> a real port within a few nm
    p, d = nearest_port(51.95, 4.05, max_nm=40.0)
    assert p is not None and d < 40.0
    # mid South Atlantic -> nothing within 50 nm
    none_p, far = nearest_port(-30.0, -20.0, max_nm=50.0)
    assert none_p is None and far > 50.0


# --------------------------------------------------------------------------- #
# AIS message parsing (pure)
# --------------------------------------------------------------------------- #
_POS = {
    "MessageType": "PositionReport",
    "MetaData": {"MMSI": 244660000, "ShipName": "TEST BULKER",
                 "time_utc": "2026-09-03 10:11:12.345 +0000 UTC"},
    "Message": {"PositionReport": {
        "Latitude": 51.9012, "Longitude": 4.1387,
        "Sog": 12.4, "Cog": 88.7, "TrueHeading": 90, "NavigationalStatus": 0,
    }},
}
_STATIC = {
    "MessageType": "ShipStaticData",
    "MetaData": {"MMSI": 244660000},
    "Message": {"ShipStaticData": {
        "Name": "TEST BULKER ", "ImoNumber": 9876543, "Type": 70,
        "Destination": "NLRTM", "MaximumStaticDraught": 12.8,
        "Eta": {"Month": 9, "Day": 5, "Hour": 6, "Minute": 30},
        "Dimension": {"A": 200, "B": 30, "C": 16, "D": 16},
    }},
}


def test_parse_position_report():
    p = parse_message(_POS)
    assert isinstance(p, AisPosition)
    assert p.mmsi == 244660000
    assert p.lat == pytest.approx(51.9012) and p.lon == pytest.approx(4.1387)
    assert p.sog_kn == pytest.approx(12.4) and p.cog_deg == pytest.approx(88.7)
    assert p.heading_deg == 90.0
    assert p.nav_status == "under way (engine)"
    assert p.ts.year == 2026 and p.ts.tzinfo is not None


def test_parse_ship_static():
    st = parse_message(_STATIC)
    assert isinstance(st, AisStatic)
    assert st.name == "TEST BULKER" and st.imo == 9876543
    assert st.destination == "NLRTM"
    assert st.eta_raw == "09-05 06:30"
    assert st.loa_m == 230.0 and st.beam_m == 32.0
    assert is_dry_bulk(st.ship_type)


def test_parse_rejects_junk_and_sentinels():
    assert parse_message({"MessageType": "Nonsense"}) is None
    assert parse_message({}) is None
    bad = {**_POS, "Message": {"PositionReport": {"Latitude": 999, "Longitude": 0}}}
    assert parse_message(bad) is None
    # SOG 102.3 / COG 360 are "not available" sentinels -> None, row still parses
    sent = {**_POS, "Message": {"PositionReport": {
        "Latitude": 10, "Longitude": 10, "Sog": 102.3, "Cog": 360.0, "TrueHeading": 511}}}
    p = parse_message(sent)
    assert p.sog_kn is None and p.cog_deg is None and p.heading_deg is None


def test_sample_is_noop_without_api_key(monkeypatch):
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    out = sample()
    assert out["ok"] is False and out["reason"] == "no api key"
    assert out["positions"] == [] and out["statics"] == []


# --------------------------------------------------------------------------- #
# /api/map/* without a database
# --------------------------------------------------------------------------- #
def test_map_ports_work_without_db(client):
    j = client.get("/api/map/ports", params={"limit": 5000}).json()
    assert j["enabled"] is True
    assert j["count"] >= 140
    p0 = j["ports"][0]
    assert {"code", "name", "lat", "lon"} <= p0.keys()


def test_map_ports_bbox_filters(client):
    # a tight box around the North Sea returns far fewer than the global set
    full = client.get("/api/map/ports", params={"limit": 8000}).json()["count"]
    box = client.get("/api/map/ports", params={"bbox": "-5,50,10,56", "limit": 8000}).json()
    assert 0 < box["count"] < full


def test_map_ports_rejects_bad_bbox(client):
    assert client.get("/api/map/ports", params={"bbox": "1,2,3"}).status_code == 400


def test_map_summary_without_db(client):
    j = client.get("/api/map/summary").json()
    assert j["enabled"] is False
    assert j["vessels"] == 0 and j["active_voyages"] == 0
    assert j["ports"] >= 140


def test_map_vessels_without_db(client):
    j = client.get("/api/map/vessels").json()
    assert j["enabled"] is False and j["vessels"] == []


def test_map_vessel_detail_without_db(client):
    j = client.get("/api/map/vessel/244660000").json()
    assert j["enabled"] is False and j["mmsi"] == 244660000

"""End-to-end smoke tests for the FreightSight API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    j = client.get("/api/health").json()
    assert j["status"] == "ok"
    assert j["series"] > 30


def test_reference_endpoints(client):
    ports = client.get("/api/reference/ports").json()
    assert len(ports["discharge_ports"]) == 7
    assert len(ports["load_ports"]) >= 10
    assert len(client.get("/api/reference/vessels").json()) == 5
    assert len(client.get("/api/reference/routes").json()) >= 15


def test_market_snapshot_rates_are_plausible(client):
    snap = client.get("/api/reference/market/snapshot").json()
    assert 300 < snap["vlsfo_usd_t"] < 1200
    for row in snap["rates"]:
        assert 2 < row["rate_usd_t"] < 90, row


def test_forecast_has_backtest_and_intervals(client):
    j = client.get("/api/forecast", params={"route_id": "AUHPT-INPRT",
                                            "vessel": "Capesize", "horizon_days": 90}).json()
    assert j["backtest"]["ensemble"]["mape"] is not None
    assert len(j["forecast"]) >= 8
    for row in j["forecast"]:
        assert row["lo"] <= row["mean"] <= row["hi"]


def test_forecast_404_for_impossible_pairing(client):
    r = client.get("/api/forecast", params={"route_id": "AUHPT-INPRT", "vessel": "Nope"})
    assert r.status_code == 404


def test_vessel_optimiser_respects_haldia_loa(client):
    r = client.post("/api/vessel/optimise", json={
        "origin": "IDMBR", "destination": "INHAL",
        "commodity": "Thermal Coal", "cargo_volume_t": 120_000})
    j = r.json()
    opts = {o["vessel"]: o for o in j["options"]}
    assert opts["Capesize"]["feasible"] is False
    assert j["recommendation"]["vessel"] in ("Supramax", "Handysize", "Panamax")


def test_capesize_feasible_into_paradip(client):
    r = client.post("/api/vessel/optimise", json={
        "origin": "AUHPT", "destination": "INPRT",
        "commodity": "Thermal Coal", "cargo_volume_t": 600_000})
    j = r.json()
    opts = {o["vessel"]: o for o in j["options"]}
    assert opts["Capesize"]["feasible"] is True
    assert j["recommendation"]["vessel"] == "Capesize"


def test_timing_recommendation_shape(client):
    r = client.post("/api/timing/recommend", json={
        "route_id": "AUHPT-INPRT", "vessel": "Capesize",
        "contract_duration_months": 6, "volume_t": 600_000})
    j = r.json()
    assert j["charter_structure"]["recommendation"] in ("SPOT", "PERIOD")
    assert j["entry_timing"]["action"] in ("WAIT", "FIX_NOW")
    assert "risk_reduction_usd" in j["vs_reactive_spot_approach"]


def test_risk_scan_and_idle(client):
    rs = client.get("/api/risk/scan").json()
    assert rs["alert_count"] >= 1
    io = client.get("/api/idle", params={"route_id": "AUHPT-INPRT", "vessel": "Capesize"}).json()
    assert 0 <= io["idle_risk_index"] <= 100
    assert all(a["route_id"] != "AUHPT-INPRT" for a in io["alternative_lanes"])


def test_full_scenario(client):
    r = client.post("/api/scenario", json={
        "origin": "AUHPT", "destination": "INPRT", "commodity": "Thermal Coal",
        "cargo_volume_t": 600_000, "contract_duration_months": 6,
        "laycan_month": 11, "forecast_horizon_days": 120})
    assert r.status_code == 200
    j = r.json()
    assert j["vessel_optimisation"]["recommendation"]["vessel"] == "Capesize"
    assert j["forecast"]["backtest"]["ensemble"]["mape"] is not None
    assert j["timing"]["charter_structure"]["recommendation"] in ("SPOT", "PERIOD")
    assert j["idle_outlook"]["idle_risk_index"] >= 0


def test_scenario_synthesized_route_degrades_gracefully(client):
    """A lane with no traded series still returns a vessel recommendation;
    forecast / timing / idle come back null rather than erroring."""
    r = client.post("/api/scenario", json={
        "origin": "USBAL", "destination": "INHAL", "commodity": "Coking Coal",
        "cargo_volume_t": 150_000, "contract_duration_months": 3,
        "forecast_horizon_days": 90})
    assert r.status_code == 200
    j = r.json()
    assert j["resolved"]["has_market_series"] is False
    assert j["vessel_optimisation"]["recommendation"]["vessel"]  # still ranked
    assert j["forecast"] is None and j["timing"] is None
    assert isinstance(j["risk_alerts"]["scoped"], list)


def test_every_discharge_port_resolves_a_scenario(client):
    ports = client.get("/api/reference/ports").json()["discharge_ports"]
    for p in ports:
        r = client.post("/api/scenario", json={
            "origin": "IDMBR", "destination": p["code"],
            "commodity": "Thermal Coal", "cargo_volume_t": 90_000,
            "contract_duration_months": 3, "forecast_horizon_days": 60})
        assert r.status_code == 200, p["code"]
        assert r.json()["vessel_optimisation"]["options"], p["code"]


def test_bad_port_code_is_rejected(client):
    r = client.post("/api/scenario", json={
        "origin": "NOPE", "destination": "INPRT", "commodity": "Thermal Coal",
        "cargo_volume_t": 100_000, "contract_duration_months": 3,
        "forecast_horizon_days": 90})
    assert r.status_code == 400


def test_forecast_intervals_widen_with_horizon(client):
    j = client.get("/api/forecast", params={
        "route_id": "IDMBR-INVTZ", "vessel": "Supramax", "horizon_days": 120}).json()
    spans = [row["hi"] - row["lo"] for row in j["forecast"]]
    assert spans[-1] >= spans[0]  # uncertainty grows further out

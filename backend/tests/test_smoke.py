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


def test_scenario_modelled_lane_returns_full_analysis(client):
    """A lane with no traded benchmark still gets forecast / timing / cover-timing
    off a modelled history, tagged series_kind='modelled'."""
    r = client.post("/api/scenario", json={
        "origin": "USBAL", "destination": "INHAL", "commodity": "Coking Coal",
        "cargo_volume_t": 150_000, "contract_duration_months": 3,
        "forecast_horizon_days": 90})
    assert r.status_code == 200
    j = r.json()
    assert j["resolved"]["has_market_series"] is False
    assert j["resolved"]["series_kind"] == "modelled"
    assert j["vessel_optimisation"]["recommendation"]["vessel"]  # still ranked
    assert j["forecast"] and len(j["forecast"]["forecast"]) >= 8
    assert j["timing"]["charter_structure"]["recommendation"] in ("SPOT", "PERIOD")
    assert j["decision_backtest"]["decision_points"] >= 4
    assert isinstance(j["risk_alerts"]["scoped"], list)


def test_scenario_accepts_any_global_port_pair(client):
    """Two ports that exist only in the global registry (never in the curated
    18) still run end to end -- routing, ranking AND a modelled forecast."""
    r = client.post("/api/scenario", json={
        "origin": "NLRTM", "destination": "CNSHG", "commodity": "Iron Ore",
        "cargo_volume_t": 160_000, "contract_duration_months": 6,
        "forecast_horizon_days": 90})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["resolved"]["series_kind"] == "modelled"
    assert j["vessel_optimisation"]["recommendation"]["vessel"]
    assert j["vessel_optimisation"]["route"]["distance_nm"] > 8000  # via Suez
    assert j["forecast"]["forecast"][0]["lo"] <= j["forecast"]["forecast"][0]["hi"]
    assert j["decision_backtest"]["decision_points"] >= 4


def test_plan_accepts_global_lanes(client):
    j = client.post("/api/plan", json={"requirements": [
        {"origin": "BRSSZ", "destination": "CNSHG", "tonnes": 300_000},
        {"origin": "AUHPT", "destination": "INPRT", "tonnes": 500_000},
    ], "horizon_months": 6}).json()
    assert len(j["lanes"]) == 2
    assert j["totals"]["tonnes"] == 800_000


def test_backtest_and_forecast_run_on_modelled_lanes(client):
    """Cover-timing back-test and forecast work for any lane; modelled lanes are
    tagged series_kind='modelled', calibrated ones 'traded'."""
    m = client.get("/api/backtest/decisions", params={
        "route_id": "NLRTM-CNSHG", "vessel": "Capesize", "contract_months": 6}).json()
    assert m["decision_points"] >= 4
    assert len(m["curve"]) == m["decision_points"]
    assert m["series_kind"] == "modelled"

    f = client.get("/api/forecast", params={
        "route_id": "FRFOS-INPRT", "vessel": "Panamax", "horizon_days": 90}).json()
    assert f["series_kind"] == "modelled"
    assert f["backtest"]["ensemble"]["mape"] is not None
    assert len(f["forecast"]) >= 8

    # a real calibrated lane still reports as traded
    t = client.get("/api/backtest/decisions", params={
        "route_id": "AUHPT-INPRT", "vessel": "Capesize", "contract_months": 6}).json()
    assert t["series_kind"] == "traded" and t["decision_points"] >= 4

    # an unknown port is still a clean 400
    assert client.post("/api/scenario", json={
        "origin": "ZZZZZ", "destination": "INPRT", "commodity": "Thermal Coal",
        "cargo_volume_t": 100_000, "contract_duration_months": 3,
        "forecast_horizon_days": 90}).status_code == 400


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


def test_forecast_backtest_reports_baselines(client):
    j = client.get("/api/forecast", params={
        "route_id": "AUHPT-INPRT", "vessel": "Capesize", "horizon_days": 120}).json()
    bt = j["backtest"]
    assert bt["baselines"]["random_walk"]["mape"] is not None
    assert bt["baselines"]["seasonal_naive"]["mape"] is not None
    assert 0.1 <= bt["ensemble_weight_holt_winters"] <= 0.9
    assert bt["skill_vs_random_walk_pct"] is not None
    assert 3.0 < bt["ensemble"]["mape"] < 35.0
    # the learned blend is no worse than its weaker component
    worse = max(m["mape"] for m in bt["models"].values())
    assert bt["ensemble"]["mape"] <= worse + 1e-6


def test_scenario_has_emissions_robustness_and_backtest(client):
    j = client.post("/api/scenario", json={
        "origin": "AUHPT", "destination": "INPRT", "cargo_volume_t": 600_000,
        "contract_duration_months": 6, "forecast_horizon_days": 120}).json()
    vo = j["vessel_optimisation"]
    assert vo["emissions"]["recommended_kt"] > 0
    assert abs(sum(vo["robustness"].values()) - 1.0) < 0.01
    assert vo["options"][0]["co2_g_per_t_nm"] > 0
    assert set(j["decision_backtest"]["strategies"]) == {
        "always_spot", "always_period", "timed_cover"}


def test_decision_backtest_endpoint(client):
    j = client.get("/api/backtest/decisions", params={
        "route_id": "IDMBR-INVTZ", "vessel": "Supramax", "contract_months": 6}).json()
    assert j["decision_points"] >= 4
    assert len(j["curve"]) == j["decision_points"]
    # locking period cover reduces cost volatility vs rolling spot
    assert j["summary"]["period_vs_spot_volatility_pct"] >= -5


def test_decision_backtest_long_contracts_do_not_400(client):
    # a 12- or 18-month cover used to raise "series too short" -- the walk-forward
    # window now widens/overlaps to keep >= 4 decision points
    for months in (9, 12, 18):
        j = client.get("/api/backtest/decisions", params={
            "route_id": "AUHPT-INPRT", "vessel": "Capesize",
            "contract_months": months}).json()
        assert j["decision_points"] >= 4, (months, j)
        assert len(j["curve"]) == j["decision_points"]
        assert j["limited_history"] is True and j["note"]
        # volatility deltas are clamped, never absurd
        for key in ("timed_vs_spot_volatility_pct", "period_vs_spot_volatility_pct"):
            assert -100.0 <= j["summary"][key] <= 100.0

    # a contract longer than the usable history still fails cleanly (validated + 400)
    assert client.get("/api/backtest/decisions", params={
        "route_id": "AUHPT-INPRT", "vessel": "Capesize", "contract_months": 30}
    ).status_code == 422  # ge/le on the query param


def test_procurement_plan(client):
    j = client.post("/api/plan", json={"requirements": [
        {"origin": "AUHPT", "destination": "INPRT", "tonnes": 900_000},
        {"origin": "IDMBR", "destination": "INVTZ", "tonnes": 400_000},
    ], "horizon_months": 6}).json()
    assert len(j["lanes"]) == 2
    assert j["totals"]["tonnes"] == 1_300_000
    for lane in j["lanes"]:
        assert 20 <= lane["period_cover_pct"] <= 80


def test_provenance_reports_data_sources(client):
    j = client.get("/api/reference/market/provenance").json()
    assert j["mode"] in ("hybrid", "synthetic")
    assert set(j["data_sources"]) == {"freight_index", "bunker", "port_activity", "weather"}

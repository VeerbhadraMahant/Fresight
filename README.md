# FreightSight — Freight Forecasting & Vessel-Chartering Decision Desk

**SIH 2026 prototype.** An intelligent, data-driven decision-support system for bulk-cargo
procurement to India's **East Coast ports** (Paradip, Visakhapatnam, Gangavaram, Gopalpur,
Dhamra, Sagar/Sandheads, Haldia). It replaces the current *reactive daily spot* approach with a
*proactive, predictive* one: forecast freight rates, pick the right vessel class against real
port constraints, time the market, and get early warnings — so the desk can move to
**short-/medium-term multiple-voyage contracts**.

---

## What it does — mapped to the problem statement

| PS ask | Where it lives | What you get |
|---|---|---|
| **Freight-rate forecasting** (ML, time-series) | `backend/app/forecasting.py` | Per route × vessel weekly forecast, 80% confidence band, monthly view, **rolling-origin backtest** (MAPE / RMSE / bias), driver diagnostics (bunker ρ, TCE ρ, congestion ρ, seasonality). Ensemble of damped Holt-Winters + seasonal-naive-with-drift. |
| **(b) Vessel-type optimisation** vs port infrastructure | `backend/app/vessel_optimizer.py` + `reference_data.py` | Rules engine over Handysize→Capesize checking **max LOA, beam, governing draft, DWT/displacement** at *both* load and discharge ports, parcel count, laytime from berth handling rate, voyage days from distance/speed, and **delivered cost/t including a priced allowance for expected port waiting time**. Returns a ranked, explained recommendation. |
| **(a) Optimal market-entry timing** | `backend/app/timing.py` | `WAIT` vs `FIX_NOW` with a concrete entry window and expected saving; **spot vs 1/3/6/12-month period charter** with expected cost *and* cost-variance, risk-adjusted; explicit comparison against the current reactive rolling-spot approach (expected saving + risk reduction). |
| **(c) Idle-scenario management** | `backend/app/idle_risk.py` (`idle_outlook`) | Idle-risk index (0–100) from demand seasonality + congestion + monsoon exposure, estimated idle days over 12 weeks, soft-demand week list, and mitigation options — including **alternative East Coast discharge ports** with lower waiting time. |
| **(d) Risk mitigation / early warnings** | `backend/app/idle_risk.py` (`scan_risks`) | Severity-ranked alert feed: volatility spikes, port-congestion build-ups, bunker surges, seasonal demand troughs, rate extremes — each with a recommended action. |
| **Dashboard** | `frontend/` | Single-screen desk: scenario form → KPI row, forecast chart with band, vessel table, timing panel, idle panel, risk feed. Dark maritime theme. |
| **One-shot "run the desk"** | `POST /api/scenario` | Enter cargo + ports + duration → the whole analysis in one response (powers the dashboard). |

---

## Architecture

```
backend/  FastAPI + pandas/statsmodels/scikit-learn
  app/
    reference_data.py   ports, vessel classes, trade routes, commodities, seasonality
                        (calibrated to public port-authority data & 2024–25 route rates)
    voyage_economics.py  bottom-up voyage estimate: hire + bunkers + port dues ÷ intake
    synthetic.py         stochastic market engine (freight, bunker, TCE, congestion, macro)
    market_store.py      startup: probe public indices (best-effort) → build dataset
    forecasting.py       HW + seasonal-naive ensemble, rolling-origin backtest, memoised
    vessel_optimizer.py  constraints rules engine → ranked recommendation
    timing.py            entry window + spot/period, risk-adjusted, vs reactive
    idle_risk.py         idle outlook + market-wide alert scan
    routers/             /api/reference/*  and  /api/{forecast,vessel,timing,risk,idle,scenario}
  tests/test_smoke.py    10 end-to-end API tests

frontend/  Vite + React + TypeScript + Tailwind + Recharts
  src/components/  ScenarioForm, Kpi, ForecastChart, VesselTable, TimingPanel, IdlePanel, RiskFeed
  src/App.tsx      layout + data flow
```

---

## Data methodology (important for judging)

There is **no free, reliable public feed** for route-level bulk freight rates (the Baltic
Exchange data is licensed). So the model runs on a **transparent synthetic market engine**,
not a black box:

1. **Fundamental value** — for every route × vessel, `voyage_economics.py` computes an
   auditable freight estimate the way a chartering desk does by hand:
   `(TCE hire × total days + bunkers + port dues + canal) ÷ (1 − commission) ÷ cargo intake`,
   with a per-route calibration factor tuned so the *latest* values land on **published
   2024–25 levels** (e.g. Capesize Australia→E.C. India ≈ \$13/t, Supramax Indonesia→E.C.
   India ≈ \$10/t, Capesize US→India ≈ \$28/t).
2. **Dynamics** — `synthetic.py` adds ~3.5 years of daily history with mean reversion,
   **regime-switching volatility** (calm/normal/stressed), an annual seasonal cycle (Indian
   restocking + SW-monsoon weather), demand shocks, route basis noise, a shared VLSFO bunker
   series, per-port congestion queues, and a few deterministic *recent* events so the live
   risk feed has something real to show on demo day.
3. **Live sanity check** — on startup the app makes a best-effort fetch of public Baltic Dry
   Index values (`market_store.py`). If reachable they're shown in the header as a reference;
   **they do not alter the modelled series**. If unreachable, the app runs fully offline.
4. **Port constraints are real** — draft/LOA/beam/DWT/handling for all 7 East Coast India
   ports and 10 origin ports are hand-curated from port-authority pages and Wikipedia, with
   sources noted inline in `reference_data.py`.

Swapping in a real historical rate feed later is a one-file change: populate
`MarketData.freight` in `market_store.py` and the forecasting/optimisation/timing layers are
unchanged.

> Prototype only — **not for operational chartering.**

---

## Running it

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
uvicorn app.main:app --port 8000  # first request builds the dataset (~3 s)
```

API docs at <http://127.0.0.1:8000/docs>. Tests: `pytest -q`.

### Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173  (proxies /api → :8000)
```

Start the backend first, then the frontend.

---

## Example API calls

```bash
# whole desk for one scenario
curl -s localhost:8000/api/scenario -H 'content-type: application/json' -d '{
  "origin":"AUHPT","destination":"INPRT","commodity":"Thermal Coal",
  "cargo_volume_t":600000,"contract_duration_months":6,"laycan_month":11,
  "forecast_horizon_days":120}' | jq

# just the forecast
curl -s 'localhost:8000/api/forecast?route_id=IDMBR-INVTZ&vessel=Supramax&horizon_days=90' | jq

# just vessel optimisation (e.g. into draft-restricted Haldia)
curl -s localhost:8000/api/vessel/optimise -H 'content-type: application/json' -d '{
  "origin":"IDMBR","destination":"INHAL","commodity":"Thermal Coal","cargo_volume_t":120000}' | jq

# market-wide risk scan
curl -s localhost:8000/api/risk/scan | jq
```

---

## Model notes & limitations

- Forecast skill is reported honestly via backtest MAPE (typically ~8–16% at 30–90 days —
  freight is genuinely volatile); the confidence band widens with √horizon from backtest
  residuals.
- The optimiser ranks on **latest** traded rate per class (fast, interactive); the forward
  view for the chosen lane is shown separately by the forecast + timing panels.
- Period-charter rates are modelled off the forward expectation + a volatility-dependent
  liquidity premium (no traded FFA/period curve available).
- Distances are great-circle × a detour factor; canal routing is a simple Atlantic→Cape-of-
  Good-Hope heuristic for undefined pairs.

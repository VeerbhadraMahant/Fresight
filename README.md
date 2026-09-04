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
| **Freight-rate forecasting** (ML, time-series) | `backend/app/forecasting.py` | Per route × vessel weekly forecast, 80% band, monthly view, **rolling-origin back-test** with **learned ensemble weights** and **baseline comparison** (random walk, seasonal naive) + a skill-vs-random-walk figure. Ensemble of damped Holt-Winters + seasonal-naive-with-drift; driver correlations (bunker ρ, TCE ρ, congestion ρ). |
| **(b) Vessel-type optimisation** vs port infrastructure | `backend/app/vessel_optimizer.py` + `reference_data.py` | Rules engine over Handysize→Capesize checking **max LOA, beam, governing draft, DWT/displacement** at *both* ports; parcel count, laytime, voyage days; **delivered cost/t including priced port-waiting + real weather-delay**; **Monte-Carlo robustness** ("optimal in N % of simulated rate paths"); **CO₂** per option (kt + g/t·nm). Ranked, explained recommendation. |
| **(a) Optimal market-entry timing** | `backend/app/timing.py` | `WAIT` vs `FIX_NOW` window + expected saving; **spot vs 1/3/6/12-month period charter**, risk-adjusted; saving + cost-risk reduction vs the reactive rolling-spot approach. |
| **Cover-timing validation** | `backend/app/decision_backtest.py` | **Walk-forward** back-test of three covering strategies — always-spot, always-period, timed — over ~2 years, on cost *and* cost-volatility. Substantiates the shift the PS asks for. |
| **Multi-cargo procurement plan** | `backend/app/procurement_planner.py` | Turns a list of forward requirements into a **recommended contract mix** — how much of each lane to lock as period/COA vs leave to spot — with plan cost, saving and risk reduction vs all-spot. |
| **(c) Idle-scenario management** | `backend/app/idle_risk.py` (`idle_outlook`) | Idle-risk index (0–100), estimated idle days / 12 wk, soft-demand weeks, alternative discharge ports. |
| **(d) Risk mitigation / early warnings** | `backend/app/idle_risk.py` (`scan_risks`) | Severity-ranked alert feed: volatility spikes, congestion build-ups, bunker surges, seasonal troughs, rate extremes — each with an action. |
| **Shipment tracking** | `backend/app/shipments.py` + `frontend` Shipments view | Each cargo booking tied to the vessel carrying it (MMSI): planned delivered cost, live position, **routed ETA** along the sea-lane graph, and a delivered-`$/t` that is **re-valued every ingest run** against fresh bunker / congestion / weather — the drift vs the baseline captured at booking is the headline. |
| **Real-time vessel map** | `edge/` (Cloudflare Worker + Durable Object) | A **viewer-gated** AIS relay: one upstream AISStream socket is opened only while someone is watching the map and closed when the last viewer leaves (zero cost when idle). Falls back to 15-min REST polling when `VITE_LIVE_WS_URL` is unset. |
| **Dashboard** | `frontend/` | Five views — **Scenario**, **Shipments**, **Procurement plan**, **Cover-timing test**, **Live map** — in a light editorial "data observatory" theme. |
| **One-shot "run the desk"** | `POST /api/scenario` | Cargo + ports + duration → the whole analysis in one response. |

---

## Data — real feeds, blended with a transparent engine

The model runs on a **hybrid** of real public data and an auditable voyage-economics engine —
not a black box, and not fully synthetic.

**Real, keyless public feeds** (`backend/app/datasources/`, committed snapshot in
`app/data/real_snapshot.json`, refreshed live on startup when reachable):

| Feed | Source | Role |
|---|---|---|
| Dry-bulk freight index | **Breakwave Dry Bulk Shipping ETF (BDRY)** — Yahoo Finance | drives the freight *regime* (the cycle every lane follows) |
| Bunker price | **Brent crude** → VLSFO estimate — Yahoo Finance | the common macro driver in the voyage model |
| Port activity | **IMF PortWatch** daily cargo calls + import tonnes (7 ports) | real congestion-waiting-days + demand signal |
| Weather | **Open-Meteo** 16-day precip / wind forecast (7 discharge ports) | weather-delay days into idle-risk and the voyage model |

**The engine on top** (`voyage_economics.py` + `synthetic.py`):

1. **Fundamental value** — per route × vessel, an auditable estimate the way a desk does it by
   hand: `(TCE hire × total days + bunkers + port dues + canal) ÷ (1 − commission) ÷ intake`,
   per-route calibrated so latest values match **published 2024–25 levels** (Capesize
   Australia→E.C. India ≈ \$13–15/t, Supramax Indonesia→E.C. India ≈ \$10–11/t, Capesize
   US→India ≈ \$30–35/t).
2. **Dynamics** — the fundamental path is multiplied by the **real BDRY regime**, given
   regime-switching volatility, an annual seasonal cycle, demand shocks and per-route basis
   noise; bunkers track real Brent; congestion is 78 % real PortWatch / 22 % stochastic
   texture where covered.
3. **Provenance** — `/api/reference/market/provenance` reports per-component status
   (`live` / `snapshot <date>` / `synthetic`); the dashboard header shows `hybrid · N/4 real
   feeds`.

Port constraints (draft / LOA / beam / DWT / handling) for all 7 East Coast India ports and 10
origin ports are hand-curated from port-authority pages and Wikipedia, cited inline in
`reference_data.py`.

`FREIGHTSIGHT_DISABLE_REALDATA=1` forces pure-synthetic; `FREIGHTSIGHT_SKIP_LIVE_PROBE=1` keeps
the committed snapshot but skips outbound refresh (the container default).

> Prototype only — **not for operational chartering.**

---

## Architecture

```
backend/  FastAPI + pandas + statsmodels
  app/
    datasources/         real feeds: BDRY, Brent, IMF PortWatch, Open-Meteo
                         (snapshot + live refresh, best-effort, deadline-bounded)
    data/real_snapshot.json   committed real-data snapshot (offline / CI safe)
    reference_data.py    ports, vessel classes, trade routes, commodities, seasonality
    voyage_economics.py  bottom-up voyage estimate
    synthetic.py         hybrid market engine (blends real feeds + stochastic overlay)
    market_store.py      startup: snapshot → build; reload() from DB; live refresh when no DB
    forecasting.py       HW + seasonal-naive ensemble (learned weights), rolling-origin
                         back-test, baselines, memoised
    vessel_optimizer.py  constraints engine + Monte-Carlo robustness + CO₂
    timing.py            entry window + spot/period, risk-adjusted, vs reactive
    decision_backtest.py walk-forward cover-timing simulation (3 strategies)
    procurement_planner.py  multi-cargo contract-mix optimiser
    idle_risk.py         idle outlook + market-wide alert scan
    db/                  SQLAlchemy models + engine (optional Postgres / Supabase;
                         app runs from bundled CSV + committed snapshot when DATABASE_URL is unset)
    geo/                 global port registry + resolver, sea-route waypoint graph,
                         any-port-to-any-port voyage economics
    live/                AIS (AISStream.io) parser + sampler · spherical dead-reckoning
    data/ports_global.csv   ~130 major world ports (merged with the 18 curated ports)
    shipments.py         cargo booking ↔ assigned vessel ↔ live delivered-cost;
                         revalue() re-runs the economics + routed ETA per ingest run
    routers/             /api/reference/*  ·  /api/{forecast,vessel,timing,risk,idle,
                         backtest/decisions,plan,scenario}  ·  /api/reference/ports/search,
                         /api/reference/port  ·  /api/geo/{route,lane}  ·
                         /api/system/{health,ingest-runs}  ·  /api/internal/refresh  ·
                         /api/map/{summary,vessels,vessel/{mmsi},ports}  ·
                         /api/shipments  (+ /{ref}, /{ref}/revalue)
  worker/ingest.py       self-updating pipeline — fetch feeds → feed_snapshots →
                         freight_rates / rate_forecasts / alerts history (runs in GitHub Actions */15)
  worker/live.py         AIS sample → positions / vessels / voyages + dead-reckoning (Phase 3)
  worker/ingest.py       ...also re-values every tracked shipment each run (Phase D)
  alembic/               0001 core+geo · 0002 history · 0003 live · 0004 forecast model · 0005 shipments
  tests/                 test_smoke.py · test_geo.py · test_worker.py · test_live.py · test_shipments.py
  edge/                  Cloudflare Worker + FleetRelay Durable Object — viewer-gated
                         live AIS relay (wss://…/ws); no DB writes, pure pass-through
  scripts/  build_real_snapshot.py · load_ports.py (seed) · import_wpi.py · start.sh (container entrypoint)
  .github/workflows/  ci.yml · ingest.yml (*/15) · keepwarm.yml (*/10)
  Dockerfile · pyproject.toml (ruff) · pytest.ini · alembic.ini · requirements*.txt · .env.example

frontend/  Vite + React + TypeScript + Tailwind + Recharts + Leaflet  ("Ventriloc" editorial theme)
  src/components/  TopBar (view nav), ScenarioPanel, StatStrip, ForecastPanel/ForecastChart,
                   VesselPanel, TimingPanel, CoverTimingPanel, IdlePanel, RiskFeed,
                   PlanView, BacktestView, MapView (react-leaflet live map), ErrorBoundary
  src/App.tsx      view router + data flow      src/lib/  theme + formatters
  Dockerfile · default.conf.template (nginx) · eslint.config.js · .env.example
```

---

## Deploy

**Recommended — Render Blueprint** (free, public URL, ~5 min, nothing to manage):

1. Push `main` to GitHub.
2. <https://dashboard.render.com> → **New → Blueprint** → pick this repo.
3. Render reads `render.yaml`, creates `freightsight-api` (Docker) + `freightsight-web`
   (static site) with the API base and CORS allow-list wired to the deterministic
   `*.onrender.com` URLs — **no manual step**. Click **Apply**.
4. Open the `freightsight-web` URL — that's the link to share. API docs at
   `freightsight-api`'s URL + `/docs`.

> Free tier: the API spins down when idle; the first hit after a pause takes ~10–20 s.
> Use the $7 Starter plan for an always-on demo.

**Alternative — Docker Compose** (VM or laptop; one URL, nginx proxies `/api`, no CORS):

```bash
docker compose up --build -d      # dashboard → :8080 · API/docs → :8000/docs
```

Full runbook, VM setup, verification and troubleshooting: **`deployment.md`** (git-ignored).

The global-scope + live-monitoring expansion is built in four phases —
[`docs/PHASES.md`](docs/PHASES.md) is the plain-language overview (what each phase
is for and how to switch it on); [`docs/GLOBAL_LIVE_MONITORING.md`](docs/GLOBAL_LIVE_MONITORING.md)
is the detailed design record.

## Running it locally

```bash
# backend  (Python 3.11+, tested on 3.13)
cd backend && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000        # instant startup (snapshot); live refresh in background
#   checks:  pip install -r requirements-dev.txt && ruff check . && python -m pytest

# frontend  (Node 18+, tested on 22)
cd frontend && npm install && npm run dev    # http://localhost:5173  (proxies /api → :8000)
#   checks:  npm run lint && npm run typecheck
```

Start the backend first. No internet required — the committed snapshot carries real numbers.

### Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `PORT` | backend / nginx | `8000` / `80` | listen port (PaaS platforms inject it) |
| `FREIGHTSIGHT_CORS_ORIGINS` | backend | `*` | comma-separated allowed origins |
| `FREIGHTSIGHT_LOG_LEVEL` | backend | `INFO` | log verbosity |
| `FREIGHTSIGHT_SKIP_LIVE_PROBE` | backend | `0` (`1` in Docker) | keep snapshot, skip live refresh |
| `FREIGHTSIGHT_DISABLE_REALDATA` | backend | `0` | pure-synthetic (no snapshot) |
| `DATABASE_URL` | backend + worker | _(unset)_ | Postgres/Supabase DSN; unset → bundled CSV + snapshot (Phase 1–3) |
| `AISSTREAM_API_KEY` | worker | _(unset)_ | AISStream.io key; unset → live-map AIS step is a no-op |
| `AIS_SAMPLE_SECONDS` | worker | `150` | AIS stream sampling window per ingest run |
| `VITE_API_BASE` | frontend (build) | `""` (same-origin `/api`) | absolute API URL if cross-origin |

---

## Example API calls

```bash
# whole desk for one scenario
curl -s localhost:8000/api/scenario -H 'content-type: application/json' -d '{
  "origin":"AUHPT","destination":"INPRT","commodity":"Thermal Coal",
  "cargo_volume_t":600000,"contract_duration_months":6,"forecast_horizon_days":120}' | jq

# forecast with baseline comparison
curl -s 'localhost:8000/api/forecast?route_id=IDMBR-INVTZ&vessel=Supramax&horizon_days=120' | jq '.backtest'

# cover-timing walk-forward back-test
curl -s 'localhost:8000/api/backtest/decisions?route_id=AUHPT-INPRT&vessel=Capesize&contract_months=6' | jq '.strategies'

# multi-cargo procurement plan
curl -s localhost:8000/api/plan -H 'content-type: application/json' -d '{
  "requirements":[{"origin":"AUHPT","destination":"INPRT","tonnes":900000},
                  {"origin":"IDMBR","destination":"INVTZ","tonnes":400000}],
  "horizon_months":6}' | jq '.totals'

# data provenance
curl -s localhost:8000/api/reference/market/provenance | jq
```

---

## Model notes & limitations

- Freight is genuinely hard to forecast; the ensemble typically beats a random-walk baseline
  but not always at every horizon — the back-test reports both, honestly, and the confidence
  band widens with √horizon from back-test residuals.
- Period-charter rates are modelled (forward expectation + small premium, or a trailing-average
  proxy in the back-test) — no traded FFA / period curve is available.
- The real-data snapshot is a point-in-time capture; the app refreshes it live when the public
  APIs are reachable, and falls back to the snapshot otherwise.
- Distances are great-circle × a detour factor; canal routing is a simple Atlantic→Cape-of-
  Good-Hope heuristic for undefined pairs.

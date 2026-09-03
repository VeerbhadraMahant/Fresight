# FreightSight — Global scope + live monitoring

Extends the SIH prototype from *fixed East-Coast-India lanes* to **any port to any
port worldwide**, and adds a **self-updating** pipeline plus a **live vessel map**.

## Decisions (locked)

| Question | Choice |
|---|---|
| Vessel-position data | **AISStream.io** (free API key, global WebSocket) for observed positions + great-circle dead-reckoning between port calls where AIS is silent. Paid feeds (Spire / MarineTraffic / Kpler) slot in later behind the same adapter. |
| Persistence | **Postgres (Supabase, free)** — position history, rate history, alerts, ingest audit. App still runs with **no DB** (bundled CSV) so local dev / CI / the current deploy are unaffected. |
| Worker | **GitHub Actions scheduled job** (`*/15`), not a paid always-on process. It has network + secrets and writes straight to Postgres, running even while the free web service sleeps. |
| Hosting | **Render free tier** for API (read-only) + static site; an external cron pinger (`*/10`) keeps it warm and current. AIS is *sampled* each worker run, not held as a persistent stream. |
| Routing / geography | **Global port set + sea-route network.** Land-avoiding distances from a maritime waypoint graph (correct canals / capes / straits); `searoute-py` is a drop-in precision upgrade. |

## Architecture

```
GitHub Actions (*/15)  ── worker/ingest.py ──►  Supabase Postgres  ◄── FastAPI API (Render, read-only)
  market feeds (BDRY, Brent)                     ports, vessels,          /api/geo/*  /api/map/*
  IMF PortWatch (all covered ports)              positions, voyages,      /api/system/health
  Open-Meteo (busy discharge ports)             freight_rates, forecasts,
  AISStream.io (bbox + fleet MMSIs, ~3 min)      alerts, ingest_runs           ▲
  voyage inference + dead-reckoning                                            │
  recompute lane rates / forecasts / alerts                          React static site (Render)
cron-job.org (*/10)  ──►  GET /api/system/health   (keep-warm)          Live map + Scenario/Plan/Backtest
```

## Phase status

- [x] **Phase 1 — Foundation** *(this change)*
  - `app/db/` — SQLAlchemy models + engine; `DATABASE_URL` optional, graceful CSV fallback.
  - `alembic/` — migration `0001` (ports, lane_geometry, ingest_runs, vessels, positions, voyages).
  - `app/data/ports_global.csv` — ~130 major world ports, merged with the 18 curated ports.
  - `app/geo/ports.py` — resolver: code / UN-LOCODE / WPI no. / name / `"lat,lon"` → `ResolvedPort`.
  - `app/geo/searoute.py` + `_searoute_graph.py` — ~100-node waypoint graph, Dijkstra, polyline geometry.
  - `app/geo/lane.py` — any-pair voyage economics (flagged `calibrated: false`).
  - Endpoints: `/api/reference/ports/search`, `/api/reference/port`, `/api/geo/route`, `/api/geo/lane`, `/api/system/health`.
  - `scripts/load_ports.py` (seed), `scripts/import_wpi.py` (real NGA Pub 150 → same table).
  - 22 new tests; ruff + full suite green; existing views unchanged.
- [ ] **Phase 2 — Self-updating pipeline** — `worker/ingest.py`, GitHub Actions cron, persisted
      rate/forecast history, `ingest_runs`-driven freshness in `/api/system/health`.
- [ ] **Phase 3 — Live map** — AIS sampling + dead-reckoning, `positions` / `voyages`,
      react-leaflet map view, vessel/port interactions.
- [ ] **Phase 4 — Polish** — system-status UI, provenance everywhere, deploy docs, tests.

## Notes / known limitations (Phase 1)

- The sea-route graph is an **estimate**: within a few percent on major lanes, looser on
  obscure ones; Chile/Peru → NE-Asia currently routes via Panama rather than the trans-Pacific
  great circle (distance is close, the map track would look wrong). `searoute-py` fixes this.
- `ports_global.csv` is a **curated** set (real coordinates, approximate drafts). Run
  `scripts/import_wpi.py <UpdatedPub150.csv>` with the authoritative NGA file for full
  ~3,700-port coverage — same table, same resolver.
- `/api/geo/lane` has **no per-lane calibration** — it is a transparent bottom-up estimate.
  The curated East-Coast-India lanes keep their calibrated `/api/scenario` path.

## Operator setup (when wiring the DB, Phase 2+)

1. Create a Supabase project → copy the connection string.
2. Render API service → env `DATABASE_URL=postgresql://...` (the container runs
   `alembic upgrade head` + `load_ports.py` on boot when it is set).
3. GitHub repo secrets: `DATABASE_URL`, `AISSTREAM_API_KEY`.
4. cron-job.org → `GET https://<api>/api/system/health` every 10 min.

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
- [x] **Phase 2 — Self-updating pipeline**
  - `alembic/` migration `0002` — `feed_snapshots`, `freight_rates`, `rate_forecasts`, `alerts`.
  - `worker/ingest.py` — one pass: fetch external feeds → stash the bundle in `feed_snapshots`
    → rebuild the hybrid dataset → append the latest rate per lane×vessel to `freight_rates`
    → snapshot every forecast to `rate_forecasts` → upsert the risk scan into `alerts` (open/expired
    lifecycle). Each step writes an `ingest_runs` row.
  - `.github/workflows/ingest.yml` (`*/15`) runs the worker; `keepwarm.yml` (`*/10`) pings the API
    and optionally POSTs `/api/internal/refresh`.
  - `load_real_data()` now prefers the worker's freshest `feed_snapshots` row over the committed
    file when a DB is configured; `market_store` skips its own HTTP refresh in that case
    (the worker owns freshness) and gains `STORE.reload()`.
  - `/api/system/health` reports per-feed freshness + `stale` flags + history counts;
    `/api/system/ingest-runs`; token-guarded `POST /api/internal/refresh`.
  - 6 new tests (subprocess-driven, real DB path); ruff + full suite green.
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

## Operator setup

Supabase project **Fresight** (`crqwjqupccutfsspdspi`, ap-southeast-1) is provisioned:
schema at `0002`, `ports` seeded (204), RLS enabled on every table (no policies — the
backend connects as table owner and bypasses RLS; the public anon API cannot read them).

1. **`DATABASE_URL`** (Supabase → Connect → *Session pooler*) set as:
   - Render `freightsight-api` env — on boot the container runs `alembic upgrade head`
     + `load_ports.py` (both no-ops now), and the app serves from the DB.
   - GitHub repo **Actions secret** — the ingest worker needs it.
2. The **ingest** workflow runs every 15 min once the secret exists (or trigger it manually
   from the Actions tab). Watch `feed_snapshots` / `freight_rates` / `ingest_runs` fill in.
3. Optional: repo variable `FREIGHTSIGHT_API_URL` + secret `FREIGHTSIGHT_REFRESH_TOKEN`
   (also set the same token on Render) to enable the keep-warm `/api/internal/refresh` POST.
4. Phase 3 only: GitHub Actions secret `AISSTREAM_API_KEY`.

Verify: `GET /api/system/health` → `self_updating: true`, `feeds.ingest.stale: false`,
`history.freight_rate_points > 0`.

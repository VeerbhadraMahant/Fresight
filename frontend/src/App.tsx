import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { api } from "./api";
import type {
  MarketSnapshot,
  Provenance,
  ScenarioRequest,
  ScenarioResponse,
  VesselRef,
} from "./types";
import { DEMO } from "./fixtures/demo";
import { TopBar, type View } from "./components/TopBar";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { StatStrip, type Stat } from "./components/StatStrip";
import { ForecastPanel } from "./components/ForecastPanel";
import { VesselPanel } from "./components/VesselPanel";
import { TimingPanel } from "./components/TimingPanel";
import { CoverTimingPanel } from "./components/CoverTimingPanel";
import { IdlePanel } from "./components/IdlePanel";
import { RiskFeed } from "./components/RiskFeed";
import { ApiErrorCard } from "./components/ApiErrorCard";

// tab-gated, chart/map-heavy -> keep them out of the initial bundle
const PlanView = lazy(() => import("./components/PlanView").then((m) => ({ default: m.PlanView })));
const BacktestView = lazy(() =>
  import("./components/BacktestView").then((m) => ({ default: m.BacktestView })),
);
const MapView = lazy(() => import("./components/MapView").then((m) => ({ default: m.MapView })));
const ShipmentsView = lazy(() =>
  import("./components/ShipmentsView").then((m) => ({ default: m.ShipmentsView })),
);

function ViewFallback() {
  return <div className="shell py-20 text-center text-slate">loading…</div>;
}
import { exportScenarioPdf } from "./lib/exportPdf";
import { pct, usdCompact } from "./lib/format";

const DEFAULT_SCENARIO = DEMO.scenarioRequest as unknown as ScenarioRequest;

// pre-computed sample so the dashboard is never empty on load
const SAMPLE = {
  vessels: DEMO.vessels as unknown as VesselRef[],
  provenance: DEMO.provenance as unknown as Provenance,
  snapshot: DEMO.snapshot as unknown as MarketSnapshot,
  result: DEMO.scenario as unknown as ScenarioResponse,
};

export default function App() {
  const [view, setView] = useState<View>("scenario");
  const [vessels, setVessels] = useState<VesselRef[]>(SAMPLE.vessels);
  const [provenance, setProvenance] = useState<Provenance | null>(SAMPLE.provenance);
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(SAMPLE.snapshot);

  const [scenario, setScenario] = useState<ScenarioRequest>(DEFAULT_SCENARIO);
  const [result, setResult] = useState<ScenarioResponse | null>(SAMPLE.result);
  const [dataMode, setDataMode] = useState<"sample" | "live">("sample");
  const [loading, setLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const loadLive = useCallback(async () => {
    setLoading(true);
    setRunError(null);
    try {
      const [v, prov, snap] = await Promise.all([
        api.vessels(),
        api.provenance(),
        api.snapshot(),
      ]);
      setVessels(v);
      setProvenance(prov);
      setSnapshot(snap);
      setResult(await api.scenario(DEFAULT_SCENARIO));
      setDataMode("live");
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const run = useCallback(async (req: ScenarioRequest) => {
    setLoading(true);
    setRunError(null);
    try {
      setResult(await api.scenario(req));
      setDataMode("live");
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLive();
  }, [loadLive]);

  const downloadPdf = useCallback(async () => {
    if (!result) return;
    setPdfBusy(true);
    setPdfError(null);
    try {
      await exportScenarioPdf(result);
    } catch (e) {
      setPdfError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setPdfBusy(false);
    }
  }, [result]);

  const stats = useMemo<Stat[] | null>(() => {
    if (!result) return null;
    const rec = result.vessel_optimisation.recommendation;
    const fc = result.forecast;
    const tim = result.timing;
    const io = result.idle_outlook;
    const db = result.decision_backtest;
    const latest = fc?.latest_rate ?? 0;
    const exp90 = fc?.expected_rate.next_90d ?? 0;
    const fcDelta = latest ? ((exp90 - latest) / latest) * 100 : 0;

    return [
      {
        label: "Recommended",
        value: rec?.vessel ?? "—",
        sub: rec ? `$${rec.delivered_cost_usd_per_t}/t · ${rec.shipments_required} shipments` : "no feasible class",
        signature: true,
      },
      {
        label: "Campaign cost",
        value: rec ? usdCompact(rec.estimated_campaign_cost_usd) : "—",
        sub: result.vessel_optimisation.emissions
          ? `${result.vessel_optimisation.emissions.recommended_kt} kt CO₂`
          : undefined,
      },
      {
        label: "Forecast 90d",
        value: fc ? `$${exp90}/t` : "—",
        sub: fc
          ? `${fcDelta <= 0 ? "▼" : "▲"} ${pct(fcDelta)} · MAPE ${fc.backtest.ensemble.mape}%`
          : "no traded series",
      },
      {
        label: "Charter call",
        value: tim?.charter_structure.recommendation ?? "—",
        sub: tim ? `entry — ${tim.entry_timing.action.replace("_", " ")}` : undefined,
      },
      {
        label: "Cost-vol cut",
        value: db ? `${db.summary.period_vs_spot_volatility_pct}%` : "—",
        sub: db ? "period cover vs spot, back-tested" : undefined,
      },
      {
        label: "Idle-risk index",
        value: io?.idle_risk_index ?? "—",
        sub: io ? `~${io.estimated_idle_days_next_12w} idle d / 12 wk` : "n/a — synth route",
      },
    ];
  }, [result]);

  return (
    <div className="min-h-dvh bg-canvas">
      <TopBar snapshot={snapshot} provenance={provenance} view={view} onView={setView} />

      {dataMode === "sample" && (
        <div className="border-b border-mist" style={{ background: "#ebe6dd" }}>
          <div className="shell flex flex-wrap items-center justify-between gap-2 py-2.5 font-sans text-[13px] text-graphite">
            <span>
              Showing a pre-computed sample scenario{loading ? " — loading live data…" : "."} The live
              API may be waking up (free tier); it refreshes automatically.
            </span>
            {!loading && (
              <button type="button" className="link" onClick={() => void loadLive()}>
                Retry now
              </button>
            )}
          </div>
        </div>
      )}

      {view === "map" && (
        <Suspense fallback={<ViewFallback />}>
          <MapView />
        </Suspense>
      )}

      {view !== "map" && (
      <section className="band-canvas">
        <div className="shell py-12 md:py-14">
          <span className="eyebrow">FreightSight</span>
          {view === "scenario" && (
            <>
              <h1 className="display mt-3 max-w-4xl text-graphite">
                From reactive spot fixtures to a predictive chartering strategy
              </h1>
              <p className="lede mt-5 max-w-2xl">
                Freight-rate forecasting, vessel-type optimisation against real port constraints,
                market-entry timing and idle-risk management for bulk cargo to India&apos;s East
                Coast ports — over real dry-bulk, bunker, port-activity and weather feeds.
              </p>

              <div className="mt-10">
                <ScenarioPanel
                  vessels={vessels}
                  value={scenario}
                  onChange={setScenario}
                  onSubmit={() => run(scenario)}
                  loading={loading}
                />
                {runError && (
                  <div className="mt-5">
                    <ApiErrorCard
                      title="Live request failed"
                      message={runError}
                      note={
                        result
                          ? "The results below are the last successful run (or the pre-computed sample). Retry when the API is reachable."
                          : undefined
                      }
                      onRetry={() => run(scenario)}
                    />
                  </div>
                )}
              </div>
            </>
          )}

          {view === "shipments" && (
            <>
              <h1 className="h-section mt-3 max-w-3xl">Shipment tracking</h1>
              <p className="lede mt-4 max-w-2xl">
                Each cargo booking, tied to the vessel carrying it — live position, routed ETA and a
                delivered&nbsp;cost/t that is re-valued against fresh bunker, congestion and weather
                every ingest run. The drift vs the baseline captured at booking is the number to
                watch.
              </p>
              <div className="mt-10">
                <Suspense fallback={<ViewFallback />}>
                  <ShipmentsView vessels={vessels} />
                </Suspense>
              </div>
            </>
          )}

          {view === "plan" && (
            <>
              <h1 className="h-section mt-3 max-w-3xl">Forward procurement planning</h1>
              <p className="lede mt-4 max-w-2xl">
                Turn a set of forward cargo requirements into a recommended contract mix — the shift
                from many single spot fixtures to fewer medium-term multiple-voyage contracts.
              </p>
              <div className="mt-10">
                <Suspense fallback={<ViewFallback />}>
                  <PlanView />
                </Suspense>
              </div>
            </>
          )}

          {view === "backtest" && (
            <>
              <h1 className="h-section mt-3 max-w-3xl">Cover-timing back-test</h1>
              <p className="lede mt-4 max-w-2xl">
                Walk-forward validation: what rolling spot, standing period cover and our timed engine
                would each have cost over the last two years.
              </p>
              <div className="mt-10">
                <Suspense fallback={<ViewFallback />}>
                  <BacktestView vessels={vessels} />
                </Suspense>
              </div>
            </>
          )}
        </div>
      </section>
      )}

      {view === "scenario" && result && stats && (
        <>
          <section className="band-ash">
            <div className="shell py-14">
              <div className="mb-6 flex flex-wrap items-baseline justify-between gap-3">
                <span className="eyebrow">headline</span>
                <div className="flex items-center gap-4">
                  <span className="meta">
                    {result.resolved.lane} · {result.resolved.vessel}
                  </span>
                  <button
                    type="button"
                    className="btn-ghost !py-1.5"
                    onClick={() => void downloadPdf()}
                    disabled={pdfBusy}
                  >
                    <Download size={14} strokeWidth={1.5} />
                    {pdfBusy ? "Preparing…" : "PDF"}
                  </button>
                </div>
              </div>
              {pdfError && <p className="meta mb-3 text-graphite">PDF export failed: {pdfError}</p>}
              <StatStrip stats={stats} />
            </div>
          </section>

          <section className="band-canvas">
            <div className="shell space-y-14 py-16">
              {result.resolved.series_kind === "modelled" && (
                <div className="card border-l-2 border-ember">
                  <p className="caption max-w-3xl text-graphite">
                    <span className="eyebrow">modelled lane</span> — {result.resolved.lane} has no
                    traded freight benchmark. The forecast, timing and cover-timing analysis below run
                    on a <em>modelled</em> price history: this lane's bottom-up voyage-economics level
                    riding the shared dry-bulk cycle, with the route's seasonal profile. Treat it as
                    directional. Calibrated East-Coast-India lanes use real traded rates.
                  </p>
                </div>
              )}
              {result.forecast ? (
                <ForecastPanel fc={result.forecast} />
              ) : (
                <div className="card-signature">
                  <h2 className="h-section">Freight forecast</h2>
                  <p className="caption mt-3 max-w-2xl">
                    Could not build a price series for {result.resolved.route_id} /{" "}
                    {result.resolved.vessel}. The vessel optimisation below still uses the
                    voyage-economics model.
                  </p>
                </div>
              )}

              <VesselPanel opt={result.vessel_optimisation} />

              {result.timing && <TimingPanel t={result.timing} />}

              {result.decision_backtest && (
                <CoverTimingPanel
                  db={result.decision_backtest}
                  months={result.request.contract_duration_months}
                />
              )}
            </div>
          </section>

          <section className="band-ash">
            <div className="shell grid gap-8 py-14 lg:grid-cols-2">
              {result.idle_outlook ? (
                <IdlePanel io={result.idle_outlook} />
              ) : (
                <div className="card-tight">
                  <h3 className="h-card">Idle-scenario management</h3>
                  <p className="caption mt-3">Not available for a synthesized route.</p>
                </div>
              )}
              <RiskFeed
                alerts={result.risk_alerts.scoped}
                counts={result.risk_alerts.severity_counts}
                totalCount={result.risk_alerts.all_count}
              />
            </div>
          </section>
        </>
      )}

      {view !== "map" && (
        <footer className="band-canvas border-t border-mist">
          <div className="shell py-8">
            <p className="meta">
              SIH 2026 prototype · real feeds (Breakwave dry-bulk index, Brent, IMF PortWatch,
              Open-Meteo) blended with a voyage-economics + stochastic engine calibrated to published
              2024–25 route rates &amp; real port constraints · not for operational chartering
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type {
  MarketSnapshot,
  PortRef,
  Provenance,
  ScenarioRequest,
  ScenarioResponse,
  VesselRef,
} from "./types";
import { TopBar } from "./components/TopBar";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { StatStrip, type Stat } from "./components/StatStrip";
import { ForecastPanel } from "./components/ForecastPanel";
import { VesselPanel } from "./components/VesselPanel";
import { TimingPanel } from "./components/TimingPanel";
import { IdlePanel } from "./components/IdlePanel";
import { RiskFeed } from "./components/RiskFeed";
import { pct, usdCompact } from "./lib/format";

const DEFAULT_SCENARIO: ScenarioRequest = {
  origin: "AUHPT",
  destination: "INPRT",
  commodity: "Thermal Coal",
  cargo_volume_t: 600000,
  contract_duration_months: 6,
  laycan_month: 11,
  vessel: null,
  forecast_horizon_days: 120,
};

export default function App() {
  const [loadPorts, setLoadPorts] = useState<PortRef[]>([]);
  const [dischargePorts, setDischargePorts] = useState<PortRef[]>([]);
  const [vessels, setVessels] = useState<VesselRef[]>([]);
  const [provenance, setProvenance] = useState<Provenance | null>(null);
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);

  const [scenario, setScenario] = useState<ScenarioRequest>(DEFAULT_SCENARIO);
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);

  const run = useCallback(async (req: ScenarioRequest) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.scenario(req));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [p, v, prov, snap] = await Promise.all([
          api.ports(),
          api.vessels(),
          api.provenance(),
          api.snapshot(),
        ]);
        setLoadPorts(p.load_ports);
        setDischargePorts(p.discharge_ports);
        setVessels(v);
        setProvenance(prov);
        setSnapshot(snap);
        await run(DEFAULT_SCENARIO);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBooting(false);
      }
    })();
  }, [run]);

  const stats = useMemo<Stat[] | null>(() => {
    if (!result) return null;
    const rec = result.vessel_optimisation.recommendation;
    const fc = result.forecast;
    const tim = result.timing;
    const io = result.idle_outlook;
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
        sub:
          rec?.potential_saving_vs_worst_feasible_usd != null
            ? `${usdCompact(rec.potential_saving_vs_worst_feasible_usd)} vs worst`
            : undefined,
      },
      {
        label: "Forecast 90d",
        value: fc ? `$${exp90}/t` : "—",
        sub: fc ? `${fcDelta <= 0 ? "▼" : "▲"} ${pct(fcDelta)} · now $${latest}/t` : "no traded series",
      },
      {
        label: "Charter call",
        value: tim?.charter_structure.recommendation ?? "—",
        sub: tim ? `entry — ${tim.entry_timing.action.replace("_", " ")}` : undefined,
      },
      {
        label: "Saving vs spot",
        value: tim ? usdCompact(tim.vs_reactive_spot_approach.expected_saving_usd) : "—",
        sub: tim
          ? `${pct(tim.vs_reactive_spot_approach.expected_saving_pct)} · risk ${usdCompact(
              -Math.abs(tim.vs_reactive_spot_approach.risk_reduction_usd),
            )}`
          : undefined,
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
      <TopBar snapshot={snapshot} provenance={provenance} />

      {/* intro + scenario */}
      <section className="band-canvas">
        <div className="shell py-14 md:py-16">
          <span className="eyebrow">FreightSight</span>
          <h1 className="display mt-3 max-w-4xl text-graphite">
            From reactive spot fixtures to a predictive chartering strategy
          </h1>
          <p className="lede mt-5 max-w-2xl">
            Freight-rate forecasting, vessel-type optimisation against real port constraints, market-entry
            timing and idle-risk management for bulk cargo to India&apos;s East Coast ports.
          </p>

          <div className="mt-10">
            {booting ? (
              <div className="card">
                <p className="caption">Building the market dataset — voyage-economics + stochastic engine…</p>
              </div>
            ) : (
              <ScenarioPanel
                loadPorts={loadPorts}
                dischargePorts={dischargePorts}
                vessels={vessels}
                value={scenario}
                onChange={setScenario}
                onSubmit={() => run(scenario)}
                loading={loading}
              />
            )}
            {error && (
              <div className="mt-5 border border-graphite bg-canvas p-5">
                <span className="font-display tracking-[-0.02em] text-graphite">Request failed.</span>{" "}
                <span className="caption">{error}</span>
              </div>
            )}
          </div>
        </div>
      </section>

      {result && stats && (
        <>
          {/* KPI band */}
          <section className="band-ash">
            <div className="shell py-14">
              <div className="mb-6 flex items-baseline justify-between">
                <span className="eyebrow">headline</span>
                <span className="meta">
                  {result.resolved.lane} · {result.resolved.vessel}
                </span>
              </div>
              <StatStrip stats={stats} />
            </div>
          </section>

          {/* analysis band */}
          <section className="band-canvas">
            <div className="shell space-y-14 py-16">
              {result.forecast ? (
                <ForecastPanel fc={result.forecast} />
              ) : (
                <div className="card-signature">
                  <h2 className="h-section">Freight forecast</h2>
                  <p className="caption mt-3 max-w-2xl">
                    No traded freight series for {result.resolved.route_id} / {result.resolved.vessel}.
                    Forecasting &amp; timing are shown only for modelled lanes; the vessel optimisation below
                    uses the voyage-economics model.
                  </p>
                </div>
              )}

              <VesselPanel opt={result.vessel_optimisation} />

              {result.timing && <TimingPanel t={result.timing} />}
            </div>
          </section>

          {/* idle + risk band */}
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

      <footer className="band-canvas border-t border-mist">
        <div className="shell py-8">
          <p className="meta">
            SIH 2026 prototype · synthetic market calibrated to published 2024–25 route rates &amp; real port
            constraints · not for operational chartering
          </p>
        </div>
      </footer>
    </div>
  );
}

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api";
import type { PlanResponse, PortRef, RequirementItem } from "../types";
import { pct, usdCompact } from "../lib/format";

const START: RequirementItem[] = [
  { origin: "AUHPT", destination: "INPRT", tonnes: 900_000 },
  { origin: "IDMBR", destination: "INVTZ", tonnes: 400_000 },
  { origin: "MZMPM", destination: "INPRT", tonnes: 250_000 },
];

export function PlanView({
  loadPorts,
  dischargePorts,
}: {
  loadPorts: PortRef[];
  dischargePorts: PortRef[];
}) {
  const [rows, setRows] = useState<RequirementItem[]>(START);
  const [months, setMonths] = useState(6);
  const [res, setRes] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (i: number, patch: Partial<RequirementItem>) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  async function run() {
    setLoading(true);
    setErr(null);
    try {
      setRes(await api.plan({ requirements: rows, horizon_months: months }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-14">
      <section className="card">
        <div className="mb-6 flex items-baseline justify-between">
          <h2 className="h-card">Forward procurement plan</h2>
          <span className="eyebrow">input</span>
        </div>
        <p className="caption mb-5 max-w-3xl">
          A set of cargo requirements over the horizon. The planner picks the vessel per lane, then
          recommends how much to lock as medium-term period / COA cover versus leave to spot —
          balancing expected cost against cost-risk.
        </p>

        <div className="space-y-3">
          {rows.map((r, i) => (
            <div key={i} className="grid grid-cols-2 gap-3 md:grid-cols-[1fr_1fr_160px_40px]">
              <select className="field" value={r.origin} onChange={(e) => set(i, { origin: e.target.value })}>
                {loadPorts.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name} · {p.country}
                  </option>
                ))}
              </select>
              <select
                className="field"
                value={r.destination}
                onChange={(e) => set(i, { destination: e.target.value })}
              >
                {dischargePorts.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name}
                  </option>
                ))}
              </select>
              <input
                type="number"
                className="field num"
                step={50_000}
                value={r.tonnes}
                onChange={(e) => set(i, { tonnes: Number(e.target.value) })}
              />
              <button
                type="button"
                className="btn-ghost !min-h-0 !p-0"
                aria-label="remove requirement"
                onClick={() => setRows(rows.filter((_, j) => j !== i))}
              >
                <Trash2 size={15} strokeWidth={1.5} />
              </button>
            </div>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-4">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setRows([...rows, { origin: "AUNTL", destination: "INGVR", tonnes: 200_000 }])}
          >
            <Plus size={15} strokeWidth={1.5} /> Add lane
          </button>
          <label className="flex items-center gap-2">
            <span className="field-label mb-0">horizon</span>
            <select
              className="field !w-auto"
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
            >
              {[3, 6, 9, 12].map((m) => (
                <option key={m} value={m}>
                  {m} months
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn-primary" onClick={run} disabled={loading || !rows.length}>
            {loading ? "Planning…" : "Build plan"}
          </button>
        </div>
        {err && <p className="caption mt-4 text-graphite">{err}</p>}
      </section>

      {res && (
        <>
          <section className="band-ash -mx-6 px-6 py-10 md:-mx-10 md:px-10">
            <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
              <Stat label="Plan cost" value={usdCompact(res.totals.plan_cost_usd)} signature />
              <Stat
                label="vs all-spot"
                value={usdCompact(res.totals.expected_saving_usd)}
                sub={pct(res.totals.expected_saving_pct)}
              />
              <Stat
                label="Cost-risk reduction"
                value={usdCompact(res.totals.cost_risk_reduction_usd)}
                sub={`${res.totals.total_co2_kt} kt CO₂`}
              />
              <Stat label="Volume planned" value={`${(res.totals.tonnes / 1e6).toFixed(2)} Mt`} />
            </div>
          </section>

          <section className="card">
            <h2 className="h-section mb-6">Recommended contract mix</h2>
            <div className="overflow-x-auto">
              <table className="obs-table min-w-[820px]">
                <thead>
                  <tr>
                    <th>Lane</th>
                    <th>Vessel</th>
                    <th className="text-right">Tonnes</th>
                    <th className="text-right">Fcst slope</th>
                    <th className="text-right">Period cover</th>
                    <th className="text-right">Period $/t</th>
                    <th className="text-right">Spot $/t</th>
                    <th className="text-right">Plan cost</th>
                    <th className="text-right">Saving</th>
                  </tr>
                </thead>
                <tbody>
                  {res.lanes.map((l) => (
                    <tr key={l.route_id}>
                      <td className="text-graphite">{l.lane}</td>
                      <td className="font-display tracking-[-0.02em]">{l.vessel}</td>
                      <td className="num text-right">{(l.tonnes / 1e3).toFixed(0)}k</td>
                      <td className="num text-right">{pct(l.forecast_slope_pct)}</td>
                      <td className="num text-right">
                        <CoverBar pct={l.period_cover_pct} />
                      </td>
                      <td className="num text-right">${l.period_rate_usd_t}</td>
                      <td className="num text-right">${l.expected_spot_usd_t}</td>
                      <td className="num text-right">{usdCompact(l.plan_cost_usd)}</td>
                      <td className="num text-right font-medium text-graphite">{usdCompact(l.saving_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  signature,
}: {
  label: string;
  value: string;
  sub?: string;
  signature?: boolean;
}) {
  return (
    <div
      className="border border-mist bg-canvas p-6"
      style={signature ? { borderRadius: "6px 0 0 0" } : { borderRadius: 8 }}
    >
      <div className="eyebrow">{label}</div>
      <div className="figure mt-2 text-[26px] leading-none text-graphite">{value}</div>
      {sub && <div className="meta mt-2">{sub}</div>}
    </div>
  );
}

function CoverBar({ pct: p }: { pct: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="inline-block h-1.5 w-16 bg-fog align-middle">
        <span className="block h-full bg-graphite" style={{ width: `${p}%` }} />
      </span>
      {p}%
    </span>
  );
}

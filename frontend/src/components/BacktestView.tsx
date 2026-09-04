import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type { DecisionBacktest, VesselRef } from "../types";
import { C } from "../lib/theme";
import { shortDate } from "../lib/format";
import { PortPicker } from "./PortPicker";

export function BacktestView({ vessels }: { vessels: VesselRef[] }) {
  const [origin, setOrigin] = useState("AUHPT");
  const [destination, setDestination] = useState("INPRT");
  const [vessel, setVessel] = useState("Capesize");
  const [months, setMonths] = useState(6);
  const [data, setData] = useState<DecisionBacktest | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const routeId = `${origin}-${destination}`;

  useEffect(() => {
    let live = true;
    setLoading(true);
    setErr(null);
    api
      .decisionBacktest(routeId, vessel, months)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [routeId, vessel, months]);

  const modelled = data?.series_kind === "modelled";
  const s = data?.strategies;

  return (
    <div className="space-y-14">
      <section className="card">
        <div className="mb-6 flex items-baseline justify-between">
          <h2 className="h-card">Cover-timing back-test</h2>
          <span className="eyebrow">walk-forward</span>
        </div>
        <p className="caption mb-5 max-w-3xl">
          Over the last ~2 years, at monthly decision points and using only prior data, what would
          each covering strategy have cost — rolling spot, standing period cover, or our timed engine?
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <PortPicker label="Load port" value={origin} onChange={setOrigin} />
          <PortPicker label="Discharge port" value={destination} onChange={setDestination} />
          <label>
            <span className="field-label">Vessel</span>
            <select className="field" value={vessel} onChange={(e) => setVessel(e.target.value)}>
              {vessels.map((v) => (
                <option key={v.name} value={v.name}>
                  {v.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Cover length</span>
            <select
              className="field"
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
        </div>
        {loading && <span className="meta mt-3 block">loading…</span>}
        {err && <p className="caption mt-4 text-graphite">{err}</p>}
        {modelled && (
          <p className="caption mt-4 max-w-3xl border-l-2 border-ember pl-4 text-graphite">
            No traded benchmark for this lane — the back-test runs on a <em>modelled</em> history
            (this lane's voyage-economics level riding the shared dry-bulk cycle). Directional, not
            a traded-index result.
          </p>
        )}
      </section>

      {data && s && (
        <section className="card-signature">
          <div className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="h-section">Cumulative cost per tonne</h2>
            <span className="meta">{data.decision_points} decision points</span>
          </div>

          {data.limited_history && (
            <p className="caption mb-5 max-w-3xl text-graphite">
              {data.note ??
                "Few non-overlapping windows fit this cover length in the available history — treat the volatility figures as indicative."}
            </p>
          )}

          <div className="mb-3 flex gap-6">
            <Key color={C.graphite} label="Always spot" />
            <Key color={C.ember} label="Timed cover" dashed />
            <Key color={C.brass} label="Always period" />
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer>
              <LineChart data={data.curve} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={C.mist} vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={shortDate}
                  minTickGap={44}
                  tickLine={false}
                  axisLine={{ stroke: C.mist }}
                  tick={{ fill: C.slate }}
                />
                <YAxis
                  width={52}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: C.slate }}
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip labelFormatter={(l) => shortDate(String(l))} />
                <Line type="monotone" dataKey="spot_cum" name="always spot" stroke={C.graphite} strokeWidth={1.6} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="period_cum" name="always period" stroke={C.brass} strokeWidth={1.6} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="timed_cum" name="timed cover" stroke={C.ember} strokeWidth={2} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-8 grid gap-5 sm:grid-cols-3">
            <StratStat name="Always spot" tag="reactive today" v={s.always_spot} />
            <StratStat name="Always period" tag="standing cover" v={s.always_period} highlight />
            <StratStat name="Timed cover" tag="our engine" v={s.timed_cover} />
          </div>

          <div className="mt-6 flex flex-wrap gap-x-8 gap-y-1.5 border-t border-mist pt-4 font-sans text-[14px] text-steel">
            <span>
              standing period cover cuts cost-volatility by{" "}
              <span className="figure text-graphite underline decoration-ember decoration-2 underline-offset-4">
                {data.summary.period_vs_spot_volatility_pct}%
              </span>{" "}
              vs rolling spot
            </span>
            <span>
              max spike avoided <span className="figure text-graphite">${data.summary.max_spike_avoided_usd_t}</span>/t
            </span>
            <span>
              {data.summary.period_locks} period locks · {data.summary.spot_periods} spot periods
            </span>
          </div>
        </section>
      )}
    </div>
  );
}

function Key({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 font-sans text-[12px] text-steel">
      <span
        className="inline-block h-0 w-5"
        style={{ borderTop: `2px ${dashed ? "dashed" : "solid"} ${color}` }}
      />
      {label}
    </span>
  );
}

function StratStat({
  name,
  tag,
  v,
  highlight,
}: {
  name: string;
  tag: string;
  v: { avg_usd_t: number; volatility_usd_t: number; worst_usd_t: number };
  highlight?: boolean;
}) {
  return (
    <div
      className="border border-mist bg-canvas p-5"
      style={highlight ? { borderRadius: "6px 0 0 0", background: "#ebe6dd" } : undefined}
    >
      <span className="eyebrow">{name}</span>
      <div className="meta">{tag}</div>
      <div className="figure mt-3 text-heading tracking-[-0.02em] text-graphite">${v.avg_usd_t}</div>
      <div className="meta">avg $/t · vol ${v.volatility_usd_t} · worst ${v.worst_usd_t}</div>
    </div>
  );
}

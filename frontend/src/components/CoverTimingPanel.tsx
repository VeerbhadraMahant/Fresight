import type { DecisionBacktestSummary, ScenarioResponse } from "../types";
import { pct } from "../lib/format";

type DB = NonNullable<ScenarioResponse["decision_backtest"]>;

export function CoverTimingPanel({ db, months }: { db: DB; months: number }) {
  const s = db.strategies;
  const sum: DecisionBacktestSummary = db.summary;
  const maxVol = Math.max(
    s.always_spot.volatility_usd_t,
    s.always_period.volatility_usd_t,
    s.timed_cover.volatility_usd_t,
  ) || 1;

  return (
    <section className="card">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h-section">Cover-timing simulation</h2>
        <span className="meta">
          walk-forward · {db.decision_points} decision points · {months}-month cover
        </span>
      </div>

      <p className="caption mb-6 max-w-3xl">
        What each covering strategy would have cost over the last ~2 years, decided only on data
        available at each point. Period cover trades a small change in average cost for a large cut
        in cost <span className="italic">volatility</span> — the move the problem statement calls for.
      </p>

      <div className="grid gap-5 sm:grid-cols-3">
        <Strat name="Always spot" tag="reactive today" stat={s.always_spot} maxVol={maxVol} />
        <Strat name="Always period" tag="standing COA cover" stat={s.always_period} maxVol={maxVol} highlight />
        <Strat name="Timed cover" tag="our engine" stat={s.timed_cover} maxVol={maxVol} />
      </div>

      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-1.5 border-t border-mist pt-4 font-sans text-[14px] text-steel">
        <span>
          standing period cover cuts cost-volatility by{" "}
          <span className="figure text-graphite underline decoration-ember decoration-2 underline-offset-4">
            {sum.period_vs_spot_volatility_pct}%
          </span>{" "}
          vs rolling spot
        </span>
        <span>
          timed cover: {pct(-sum.timed_vs_spot_cost_pct)} cost · {sum.timed_vs_spot_volatility_pct}%
          less volatile · {sum.period_locks} locks
        </span>
        <span>
          worst month — spot <span className="figure text-graphite">${sum.worst_period_spot_usd_t}</span>/t
          vs timed <span className="figure text-graphite">${sum.worst_period_timed_usd_t}</span>/t
        </span>
        <span>
          max spike avoided{" "}
          <span className="figure text-graphite">${sum.max_spike_avoided_usd_t}</span>/t
        </span>
      </div>
    </section>
  );
}

function Strat({
  name,
  tag,
  stat,
  maxVol,
  highlight,
}: {
  name: string;
  tag: string;
  stat: { avg_usd_t: number; volatility_usd_t: number; worst_usd_t: number };
  maxVol: number;
  highlight?: boolean;
}) {
  return (
    <div
      className="border border-mist bg-canvas p-5"
      style={highlight ? { borderRadius: "6px 0 0 0", background: "#ebe6dd" } : undefined}
    >
      <span className="eyebrow">{name}</span>
      <div className="meta">{tag}</div>
      <div className="figure mt-3 text-heading tracking-[-0.02em] text-graphite">${stat.avg_usd_t}</div>
      <div className="meta">avg $/t over the horizon</div>
      <div className="mt-3">
        <div className="flex justify-between font-sans text-[12px] text-slate">
          <span>cost volatility</span>
          <span className="figure">${stat.volatility_usd_t}/t</span>
        </div>
        <div className="mt-1 h-2 w-full bg-fog">
          <div
            className="h-full"
            style={{
              width: `${(stat.volatility_usd_t / maxVol) * 100}%`,
              background: highlight ? "#202020" : "#b8b8b8",
            }}
          />
        </div>
      </div>
      <div className="meta mt-2">worst period ${stat.worst_usd_t}/t</div>
    </div>
  );
}

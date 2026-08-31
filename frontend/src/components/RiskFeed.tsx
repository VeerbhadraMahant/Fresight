import type { RiskAlert } from "../types";

const CATEGORY: Record<string, string> = {
  volatility: "Volatility",
  port_congestion: "Port congestion",
  bunker: "Bunker",
  seasonal_demand: "Seasonal demand",
  rate_extreme: "Rate extreme",
};

const SEV_CLASS: Record<string, string> = {
  critical: "sev-high",
  high: "sev-high",
  medium: "sev-medium",
  low: "sev-low",
  info: "sev-low",
};

export function RiskFeed({
  alerts,
  counts,
  totalCount,
}: {
  alerts: RiskAlert[];
  counts: Record<string, number>;
  totalCount: number;
}) {
  const order = ["critical", "high", "medium", "low", "info"];
  return (
    <section className="card-tight flex h-full flex-col">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="h-card">Risk &amp; early warnings</h3>
        <div className="flex flex-wrap gap-1.5">
          {order
            .filter((s) => counts[s])
            .map((s) => (
              <span key={s} className="tag">
                {counts[s]} {s}
              </span>
            ))}
        </div>
      </div>

      <div className="flex-1 space-y-3">
        {alerts.length === 0 && (
          <p className="caption py-6 text-center">
            No alerts scoped to this lane. Conditions are benign.
          </p>
        )}
        {alerts.map((a) => (
          <article key={a.id} className={`bg-fog py-2.5 pl-3.5 pr-3 ${SEV_CLASS[a.severity]}`}>
            <div className="flex items-baseline justify-between">
              <span className="eyebrow">{CATEGORY[a.category] ?? a.category}</span>
              <span className="meta uppercase tracking-[0.08em]">{a.severity}</span>
            </div>
            <p className="mt-1 font-sans text-[13px] leading-relaxed text-graphite">{a.message}</p>
            <p className="mt-1 font-sans text-[12px] leading-relaxed text-steel">
              <span className="text-ember">→</span> {a.recommended_action}
            </p>
          </article>
        ))}
      </div>

      <p className="meta mt-4 border-t border-mist pt-3">
        {alerts.length} lane-scoped of {totalCount} market-wide alerts
      </p>
    </section>
  );
}

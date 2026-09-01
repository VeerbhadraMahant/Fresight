import type { MarketSnapshot, Provenance } from "../types";
import { pct } from "../lib/format";

const VIEWS = [
  ["scenario", "Scenario"],
  ["plan", "Procurement plan"],
  ["backtest", "Cover-timing test"],
] as const;

export type View = (typeof VIEWS)[number][0];

export function TopBar({
  snapshot,
  provenance,
  view,
  onView,
}: {
  snapshot: MarketSnapshot | null;
  provenance: Provenance | null;
  view: View;
  onView: (v: View) => void;
}) {
  const liveCount = provenance
    ? Object.values(provenance.data_sources).filter((s) => s.includes("live") || s.includes("snapshot")).length
    : 0;

  return (
    <header className="border-b border-mist bg-canvas">
      <div className="shell flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-5">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[22px] tracking-[-0.02em] text-graphite">FreightSight</span>
          <span className="hidden font-display text-[13px] tracking-[-0.02em] text-slate md:inline">
            charter decision observatory
          </span>
        </div>

        <nav className="nav-pill" aria-label="views">
          {VIEWS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => onView(id)}
              className={`rounded-pill px-3 py-1 transition-colors ${
                view === id ? "bg-graphite text-canvas" : "text-steel hover:text-graphite"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>

        {provenance && (
          <div
            className="meta max-w-[320px] text-right"
            title={
              `${provenance.note}\n\n` +
              Object.entries(provenance.data_sources)
                .map(([k, v]) => `${k}: ${v}`)
                .join("\n") +
              `\n\nHistory ${provenance.history_start} → ${provenance.history_end} · ${provenance.series_count} series`
            }
          >
            <span className="link">{provenance.mode}</span> · {liveCount}/4 real feeds
            {snapshot && (
              <>
                {" · "}
                VLSFO <span className="num text-graphite">${snapshot.vlsfo_usd_t}</span>{" "}
                <span className={snapshot.vlsfo_change_30d_pct >= 0 ? "text-graphite" : "text-slate"}>
                  {pct(snapshot.vlsfo_change_30d_pct)}
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

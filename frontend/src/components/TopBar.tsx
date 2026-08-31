import type { MarketSnapshot, Provenance } from "../types";
import { pct } from "../lib/format";

export function TopBar({
  snapshot,
  provenance,
}: {
  snapshot: MarketSnapshot | null;
  provenance: Provenance | null;
}) {
  return (
    <header className="border-b border-mist bg-canvas">
      <div className="shell flex flex-wrap items-center justify-between gap-4 py-5">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[22px] tracking-[-0.02em] text-graphite">FreightSight</span>
          <span className="hidden font-display text-[13px] tracking-[-0.02em] text-slate sm:inline">
            charter decision observatory
          </span>
        </div>

        {snapshot && (
          <div className="nav-pill">
            <span>
              VLSFO{" "}
              <span className="num text-graphite">${snapshot.vlsfo_usd_t}</span>
              <span className="ml-1 text-slate">{pct(snapshot.vlsfo_change_30d_pct)}</span>
            </span>
            <span className="h-3 w-px bg-mist" />
            <span className="text-slate">as of {snapshot.as_of}</span>
          </div>
        )}

        {provenance && (
          <div
            className="meta max-w-[280px] text-right"
            title={`${provenance.note}\n\nHistory: ${provenance.history_start} → ${provenance.history_end}\nAttempted: ${provenance.attempted_sources.join(
              ", ",
            )}\nLive points: ${
              provenance.live_points.map((l) => `${l.label}=${l.value}`).join("; ") || "none"
            }`}
          >
            <span className="link">{provenance.mode}</span> · {provenance.series_count} modelled series
          </div>
        )}
      </div>
    </header>
  );
}

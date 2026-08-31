import type { ReactNode } from "react";

export interface Stat {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  signature?: boolean;
}

export function StatStrip({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-6">
      {stats.map((s) => (
        <div
          key={String(s.label)}
          className={`bg-canvas p-6 ${s.signature ? "" : "rounded-card"} border border-mist`}
          style={s.signature ? { borderRadius: "6px 0 0 0" } : undefined}
        >
          <div className="eyebrow">{s.label}</div>
          <div className="figure mt-2 text-[26px] leading-none text-graphite">{s.value}</div>
          {s.sub && <div className="meta mt-2 leading-snug">{s.sub}</div>}
        </div>
      ))}
    </div>
  );
}

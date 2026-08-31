import type { IdleOutlook } from "../types";

export function IdlePanel({ io }: { io: IdleOutlook }) {
  return (
    <section className="card-tight">
      <div className="mb-5 flex items-baseline justify-between">
        <h3 className="h-card">Idle-scenario management</h3>
        <span className="meta">{io.lane}</span>
      </div>

      <div className="flex items-center gap-6">
        <Ring value={io.idle_risk_index} />
        <div className="flex-1">
          <div className="figure text-[30px] leading-none text-graphite">{io.idle_risk_index}</div>
          <div className="meta mt-1">
            idle-risk index · ~{io.estimated_idle_days_next_12w} idle days over 12 weeks
          </div>
          <div className="mt-3 space-y-1.5">
            {Object.entries(io.components).map(([k, v]) => (
              <Bar key={k} label={k.replace(/_/g, " ")} value={v} />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-5 border-t border-mist pt-4">
        <div>
          <span className="eyebrow">discharge wait now</span>
          <div className="figure text-subheading text-graphite">{io.discharge_wait_days_now} d</div>
          <div className="meta">year avg {io.discharge_wait_days_year_avg} d</div>
        </div>
        <div>
          <span className="eyebrow">soft-demand weeks · next 12</span>
          <div className="figure text-subheading text-graphite">{io.soft_demand_weeks.length}</div>
          <div className="meta">{io.soft_demand_weeks.slice(0, 3).map((w) => w.week).join(" · ") || "none"}</div>
        </div>
      </div>

      {io.alternative_lanes.length > 0 && (
        <div className="mt-4">
          <span className="eyebrow">alternative discharge options</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {io.alternative_lanes.map((a) => (
              <span key={a.route_id} className="tag-warm">
                {a.lane.split("->")[1]?.trim()} · {a.discharge_wait_days} d · demand {a.near_term_demand_factor}
              </span>
            ))}
          </div>
        </div>
      )}

      <ul className="mt-4 space-y-2">
        {io.mitigation.map((m, i) => (
          <li key={i} className="flex gap-2.5 font-sans text-[13px] leading-relaxed text-steel">
            <span className="mt-2 h-1 w-1 shrink-0 bg-ember" />
            {m}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Ring({ value }: { value: number }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const off = circ - (Math.min(Math.max(value, 0), 100) / 100) * circ;
  return (
    <svg width="76" height="76" viewBox="0 0 76 76" className="-rotate-90 shrink-0">
      <circle cx="38" cy="38" r={r} fill="none" stroke="#e8e8e8" strokeWidth="4" />
      <circle
        cx="38"
        cy="38"
        r={r}
        fill="none"
        stroke="#ff682c"
        strokeWidth="4"
        strokeDasharray={circ}
        strokeDashoffset={off}
      />
    </svg>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 font-sans text-[12px]">
      <span className="w-36 shrink-0 text-slate">{label}</span>
      <div className="h-1.5 flex-1 bg-fog">
        <div className="h-full bg-graphite" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className="num w-7 text-right text-steel">{value}</span>
    </div>
  );
}

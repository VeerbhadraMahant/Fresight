import { Check, X } from "lucide-react";
import type { ScenarioResponse } from "../types";
import { num, usdCompact } from "../lib/format";

export function VesselPanel({ opt }: { opt: ScenarioResponse["vessel_optimisation"] }) {
  const rec = opt.recommendation;
  const lp = opt.constraints.load_port;
  const dp = opt.constraints.discharge_port;

  return (
    <section className="card">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h-section">Vessel-type optimisation</h2>
        <span className="meta">
          bunker ${opt.bunker_used_usd_t}/t · {opt.route.distance_nm} nm
          {opt.route.canal !== "none" ? ` · ${opt.route.canal}` : ""}
        </span>
      </div>

      {rec && (
        <div className="mb-8 p-6" style={{ background: "#ebe6dd", borderRadius: "6px 0 0 0" }}>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <span className="eyebrow">recommendation</span>
              <div className="font-display text-heading tracking-[-0.02em] text-graphite">{rec.vessel}</div>
            </div>
            <div className="figure text-right text-[15px] text-graphite">
              <div>${rec.delivered_cost_usd_per_t}/t delivered</div>
              <div className="meta mt-0.5">
                {rec.shipments_required} shipment{rec.shipments_required > 1 ? "s" : ""} ·{" "}
                {usdCompact(rec.estimated_campaign_cost_usd)} campaign
              </div>
            </div>
          </div>
          <p className="caption mt-3 max-w-3xl">{rec.why}</p>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-sans text-[13px] text-graphite">
            {rec.potential_saving_vs_worst_feasible_usd != null && (
              <span>
                up to <span className="link">{usdCompact(rec.potential_saving_vs_worst_feasible_usd)}</span> vs
                worst feasible class
              </span>
            )}
            {opt.robustness?.[rec.vessel] != null && (
              <span>
                optimal in{" "}
                <span className="figure">{Math.round(opt.robustness[rec.vessel] * 100)}%</span> of simulated
                rate paths
              </span>
            )}
            {opt.emissions && (
              <span>
                <span className="figure">{opt.emissions.recommended_kt} kt</span> CO₂ ·{" "}
                {opt.emissions.recommended_vs_greenest_pct === 0
                  ? "greenest feasible class"
                  : `+${opt.emissions.recommended_vs_greenest_pct}% vs ${opt.emissions.greenest_feasible}`}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="obs-table min-w-[820px]">
          <thead>
            <tr>
              <th>Class</th>
              <th className="text-right">Intake t</th>
              <th className="text-right">Ships</th>
              <th className="text-right">Gov. draft</th>
              <th className="text-right">DWT util</th>
              <th className="text-right">Freight $/t</th>
              <th className="text-right">Wait d</th>
              <th className="text-right">Delivered $/t</th>
              <th className="text-right">CO₂ g/t·nm</th>
              <th className="text-right">Robust</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {opt.options.map((o) => {
              const isRec = rec?.vessel === o.vessel;
              const robust = opt.robustness?.[o.vessel];
              return (
                <tr
                  key={o.vessel}
                  className={isRec ? "" : o.feasible ? "" : "opacity-45"}
                  style={isRec ? { background: "#f5f5f5" } : undefined}
                >
                  <td className="font-display tracking-[-0.02em] text-graphite">{o.vessel}</td>
                  <td className="num text-right">{num(o.intake_t)}</td>
                  <td className="num text-right">{o.shipments_required}</td>
                  <td className="num text-right">{o.governing_draft_m} m</td>
                  <td className="num text-right">{o.draft_utilisation_pct}%</td>
                  <td className="num text-right">${o.freight_usd_per_t}</td>
                  <td
                    className="num text-right"
                    title={o.weather_delay_days ? `incl. ${o.weather_delay_days} d weather delay` : undefined}
                  >
                    {o.expected_wait_days}
                    {o.weather_delay_days > 0 && <span className="text-ember"> ◦</span>}
                  </td>
                  <td className="num text-right font-medium text-graphite">${o.delivered_cost_usd_per_t}</td>
                  <td className="num text-right">{o.co2_g_per_t_nm}</td>
                  <td className="num text-right">
                    {robust != null ? `${Math.round(robust * 100)}%` : "—"}
                  </td>
                  <td>
                    {o.feasible ? (
                      <span className="inline-flex items-center gap-1.5 text-steel">
                        <Check size={13} strokeWidth={1.75} /> feasible
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1.5 text-slate"
                        title={o.reasons.join(" · ")}
                      >
                        <X size={13} strokeWidth={1.75} /> {o.reasons[0]}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid gap-5 border-t border-mist pt-5 sm:grid-cols-2">
        {[
          { p: lp, tag: "Load port" },
          { p: dp, tag: "Discharge port" },
        ].map(({ p, tag }) => (
          <div key={tag}>
            <span className="eyebrow">{tag}</span>
            <div className="font-display text-subheading tracking-[-0.02em] text-graphite">{p.name}</div>
            <p className="meta mt-1">
              draft {p.max_draft_m} m · LOA {p.max_loa_m} m · beam {p.max_beam_m} m · max {num(p.max_dwt)} DWT ·{" "}
              {num(p.handling_tpd)} t/day{p.transload ? " · anchorage transload" : ""}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

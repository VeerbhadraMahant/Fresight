import type { ScenarioResponse } from "../types";
import { usd, usdCompact, num } from "./format";

/**
 * Build a one-page "Charter Recommendation" PDF from a scenario result.
 * jsPDF is loaded on demand so it never touches the initial bundle or the
 * first paint; a failure here just throws and is surfaced as a toast.
 */
export async function exportScenarioPdf(r: ScenarioResponse): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "pt", format: "a4" });

  const M = 48;
  let y = M;
  const W = doc.internal.pageSize.getWidth();

  const H = (t: string, size = 11, gap = 16) => {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(size);
    doc.text(t, M, y);
    y += gap;
  };
  const P = (t: string, gap = 13) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.splitTextToSize(t, W - 2 * M).forEach((line: string) => {
      doc.text(line, M, y);
      y += gap;
    });
  };
  const rule = () => {
    doc.setDrawColor(210);
    doc.line(M, y, W - M, y);
    y += 14;
  };
  const kv = (pairs: [string, string][]) => {
    doc.setFontSize(9);
    pairs.forEach(([k, v]) => {
      doc.setFont("helvetica", "normal");
      doc.setTextColor(120);
      doc.text(k, M, y);
      doc.setTextColor(20);
      doc.setFont("helvetica", "bold");
      doc.text(v, M + 190, y);
      y += 14;
    });
    doc.setTextColor(20);
  };

  const opt = r.vessel_optimisation;
  const rec = opt.recommendation;
  const fc = r.forecast;
  const tim = r.timing;
  const db = r.decision_backtest;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("FreightSight — Charter Recommendation", M, y);
  y += 18;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(120);
  doc.text(
    `${opt.route.lane ?? r.resolved.lane}  ·  generated ${new Date().toISOString().slice(0, 16).replace("T", " ")} UTC`,
    M,
    y,
  );
  doc.setTextColor(20);
  y += 20;
  rule();

  H("Cargo");
  kv([
    ["Commodity", opt.cargo.commodity],
    ["Campaign volume", `${num(opt.cargo.volume_t)} t`],
    ["Contract duration", `${r.request.contract_duration_months} months`],
    ["Load port", `${opt.constraints.load_port.name} (draft ${opt.constraints.load_port.max_draft_m} m)`],
    ["Discharge port", `${opt.constraints.discharge_port.name} (draft ${opt.constraints.discharge_port.max_draft_m} m)`],
  ]);
  y += 4;
  rule();

  if (rec) {
    H("Recommendation");
    kv([
      ["Vessel class", rec.vessel],
      ["Delivered cost", `${usd(rec.delivered_cost_usd_per_t, 2)}/t`],
      ["Shipments", String(rec.shipments_required)],
      ["Estimated campaign cost", usdCompact(rec.estimated_campaign_cost_usd)],
      ...(opt.robustness?.[rec.vessel] != null
        ? ([["Robustness", `optimal in ${Math.round(opt.robustness[rec.vessel] * 100)}% of simulated rate paths`]] as [string, string][])
        : []),
      ...(opt.emissions
        ? ([["Emissions", `${opt.emissions.recommended_kt} kt CO2 (${opt.emissions.recommended_g_per_t_nm} g/t-nm)`]] as [string, string][])
        : []),
    ]);
    P(rec.why);
    y += 4;
    rule();
  }

  // vessel options table
  H("Vessel options");
  const cols = [M, M + 90, M + 150, M + 220, M + 300, M + 380, M + 470];
  const head = ["Class", "Intake t", "Ships", "Freight $/t", "Delivered $/t", "CO2 g/t-nm", "Status"];
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  head.forEach((h, i) => doc.text(h, cols[i], y));
  y += 12;
  doc.setFont("helvetica", "normal");
  opt.options.forEach((o) => {
    const row = [
      o.vessel,
      num(o.intake_t),
      String(o.shipments_required),
      `$${o.freight_usd_per_t}`,
      `$${o.delivered_cost_usd_per_t}`,
      String(o.co2_g_per_t_nm),
      o.feasible ? "feasible" : (o.reasons[0] ?? "infeasible").slice(0, 34),
    ];
    row.forEach((c, i) => doc.text(String(c), cols[i], y));
    y += 12;
  });
  y += 6;
  rule();

  if (fc) {
    H("Freight forecast");
    kv([
      ["Model", fc.model],
      ["Latest", `$${fc.latest_rate}/t`],
      ["Expected 30 / 60 / 90 d", `$${fc.expected_rate.next_30d} / $${fc.expected_rate.next_60d} / $${fc.expected_rate.next_90d}/t`],
      ["Back-test MAPE / RMSE", `${fc.backtest.ensemble.mape}% / $${fc.backtest.ensemble.rmse}`],
      ["Baselines", `random walk ${fc.backtest.baselines.random_walk.mape}% · seasonal naive ${fc.backtest.baselines.seasonal_naive.mape}%`],
      ["Skill vs random walk", `${fc.backtest.skill_vs_random_walk_pct}%`],
    ]);
    y += 4;
    rule();
  }

  if (tim) {
    H("Market-entry timing");
    kv([
      ["Entry decision", tim.entry_timing.action.replace("_", " ")],
      ["Charter structure", `${tim.charter_structure.recommendation} (${tim.charter_structure.contract_duration_months} mo)`],
      ["Rolling spot", `$${tim.charter_structure.spot.expected_rate_usd_t}/t → ${usdCompact(tim.charter_structure.spot.expected_cost_usd)}`],
      ["Period charter", `$${tim.charter_structure.period.indicative_rate_usd_t}/t → ${usdCompact(tim.charter_structure.period.expected_cost_usd)}`],
      ["Saving vs reactive spot", `${usdCompact(tim.vs_reactive_spot_approach.expected_saving_usd)} (${tim.vs_reactive_spot_approach.expected_saving_pct}%)`],
    ]);
    y += 4;
    rule();
  }

  if (db) {
    H("Cover-timing back-test");
    kv([
      ["Always spot", `$${db.strategies.always_spot.avg_usd_t}/t avg · vol $${db.strategies.always_spot.volatility_usd_t}`],
      ["Always period", `$${db.strategies.always_period.avg_usd_t}/t avg · vol $${db.strategies.always_period.volatility_usd_t}`],
      ["Timed cover", `$${db.strategies.timed_cover.avg_usd_t}/t avg · vol $${db.strategies.timed_cover.volatility_usd_t}`],
      ["Period cover cost-volatility", `${db.summary.period_vs_spot_volatility_pct}% lower vs rolling spot`],
    ]);
  }

  doc.setFontSize(7.5);
  doc.setTextColor(140);
  doc.text(
    "FreightSight — SIH 2026 prototype. Hybrid model (real dry-bulk / bunker / port-activity / weather feeds + voyage-economics engine). Not for operational chartering.",
    M,
    doc.internal.pageSize.getHeight() - 28,
    { maxWidth: W - 2 * M },
  );

  const safe = (opt.route.lane ?? "scenario").replace(/[^\w]+/g, "-").toLowerCase();
  doc.save(`freightsight-${safe}.pdf`);
}

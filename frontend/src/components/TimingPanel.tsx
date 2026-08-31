import type { Timing } from "../types";
import { pct, usdCompact } from "../lib/format";

export function TimingPanel({ t }: { t: Timing }) {
  const cs = t.charter_structure;
  const vr = t.vs_reactive_spot_approach;
  const wait = t.entry_timing.action === "WAIT";
  const period = cs.recommendation === "PERIOD";
  const maxCost = Math.max(cs.spot.expected_cost_usd, cs.period.expected_cost_usd) || 1;

  return (
    <section className="card">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h-section">Market-entry timing &amp; contract structure</h2>
        <span className="meta">
          volatility {pct(t.annualised_volatility_pct)} p.a. · forecast slope {pct(t.forecast_slope_over_contract_pct)}
        </span>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        {/* entry decision */}
        <div>
          <div className="flex items-baseline justify-between">
            <span className="eyebrow">entry decision</span>
            <span className="tag-strong">{t.entry_timing.action.replace("_", " ")}</span>
          </div>
          <div className="figure mt-3 text-heading tracking-[-0.02em] text-graphite">
            {wait
              ? `${t.entry_timing.window.from} → ${t.entry_timing.window.to}`
              : "Fix promptly"}
          </div>
          {t.entry_timing.expected_saving_usd > 0 && (
            <p className="mt-1 font-sans text-[13px] text-graphite">
              ~<span className="link">{usdCompact(t.entry_timing.expected_saving_usd)}</span> expected saving by
              waiting
            </p>
          )}
          <p className="caption mt-3">{t.entry_timing.rationale}</p>
        </div>

        {/* charter structure */}
        <div>
          <div className="flex items-baseline justify-between">
            <span className="eyebrow">charter structure · {cs.contract_duration_months} mo</span>
            <span className="tag-strong">{cs.recommendation}</span>
          </div>

          <div className="mt-4 space-y-4">
            <CostBar
              label={`Rolling spot · $${cs.spot.expected_rate_usd_t}/t`}
              cost={cs.spot.expected_cost_usd}
              std={cs.spot.cost_std_usd}
              max={maxCost}
              chosen={!period}
            />
            <CostBar
              label={`${cs.contract_duration_months}-mo period · $${cs.period.indicative_rate_usd_t}/t`}
              cost={cs.period.expected_cost_usd}
              std={cs.period.cost_std_usd}
              max={maxCost}
              chosen={period}
            />
          </div>
          <p className="caption mt-3">{cs.rationale}</p>
        </div>
      </div>

      <div className="mt-8 border-t border-mist pt-5">
        <span className="eyebrow">vs. current reactive spot approach</span>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-8 gap-y-1.5 font-sans text-[14px] text-steel">
          <span>
            Expected cost{" "}
            <span className="figure text-graphite">{usdCompact(vr.expected_saving_usd)}</span>{" "}
            <span className="meta">({pct(vr.expected_saving_pct)})</span>
          </span>
          <span>
            Cost-risk reduction{" "}
            <span className="figure text-graphite">{usdCompact(vr.risk_reduction_usd)}</span>
          </span>
          <span className="meta">flat-rate reference {usdCompact(vr.flat_rate_reference_cost_usd)}</span>
        </div>
        <p className="meta mt-2 max-w-3xl leading-relaxed">{vr.note}</p>
      </div>
    </section>
  );
}

function CostBar({
  label,
  cost,
  std,
  max,
  chosen,
}: {
  label: string;
  cost: number;
  std: number;
  max: number;
  chosen: boolean;
}) {
  const w = (cost / max) * 100;
  const stdW = Math.min((std / max) * 100, w);
  return (
    <div>
      <div className="flex items-baseline justify-between font-sans text-[13px]">
        <span className={chosen ? "text-graphite underline decoration-ember decoration-2 underline-offset-4" : "text-steel"}>
          {label}
        </span>
        <span className="figure text-graphite">
          {usdCompact(cost)} <span className="text-slate">± {usdCompact(std)}</span>
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full bg-fog">
        <div
          className="relative h-full"
          style={{ width: `${w}%`, background: chosen ? "#202020" : "#b8b8b8" }}
        >
          <div
            className="absolute right-0 top-0 h-full"
            style={{ width: `${(stdW / w) * 100}%`, background: "#ffffff", opacity: 0.35 }}
          />
        </div>
      </div>
    </div>
  );
}

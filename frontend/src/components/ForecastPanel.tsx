import type { Forecast } from "../types";
import { ForecastChart } from "./ForecastChart";

export function ForecastPanel({ fc }: { fc: Forecast }) {
  const bt = fc.backtest.ensemble;
  const drivers = Object.entries(fc.drivers).filter(([, v]) => v != null) as [string, number][];

  return (
    <section className="card-signature">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h-section">Freight forecast</h2>
        <span className="meta">
          {fc.route_id} · {fc.vessel} · {fc.model}
        </span>
      </div>

      <dl className="mb-8 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
        <Metric term="Latest" value={`$${fc.latest_rate}/t`} />
        <Metric term="Expected 30 / 60 / 90 d" value={`$${fc.expected_rate.next_30d} · $${fc.expected_rate.next_60d} · $${fc.expected_rate.next_90d}`} />
        <Metric term="Backtest MAPE / RMSE" value={`${bt.mape ?? "—"}% · $${bt.rmse ?? "—"}`} emphasis />
        <Metric term="12-month percentile" value={`${fc.current_percentile_12m}`} />
      </dl>

      <ForecastChart fc={fc} />

      <div className="mt-6 border-t border-mist pt-4">
        <span className="eyebrow">drivers · trailing 12 months (ρ)</span>
        <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1.5 font-sans text-[13px] text-steel">
          {drivers.map(([k, v]) => (
            <span key={k}>
              {k.replace(/_/g, " ").replace(" corr", "")}{" "}
              <span className="num text-graphite">{v.toFixed(2)}</span>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Metric({ term, value, emphasis }: { term: string; value: string; emphasis?: boolean }) {
  return (
    <div>
      <dt className="field-label mb-1">{term}</dt>
      <dd className={`figure text-[17px] ${emphasis ? "text-graphite underline decoration-ember decoration-2 underline-offset-4" : "text-graphite"}`}>
        {value}
      </dd>
    </div>
  );
}

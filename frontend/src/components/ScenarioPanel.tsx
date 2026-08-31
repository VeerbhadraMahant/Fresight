import type { PortRef, ScenarioRequest, VesselRef } from "../types";
import { MONTH_NAMES } from "../lib/format";

const COMMODITIES = ["Thermal Coal", "Coking Coal", "Iron Ore", "Bauxite", "Limestone"];
const DURATIONS = [1, 3, 6, 12];

export function ScenarioPanel({
  loadPorts,
  dischargePorts,
  vessels,
  value,
  onChange,
  onSubmit,
  loading,
}: {
  loadPorts: PortRef[];
  dischargePorts: PortRef[];
  vessels: VesselRef[];
  value: ScenarioRequest;
  onChange: (v: ScenarioRequest) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  const set = <K extends keyof ScenarioRequest>(k: K, v: ScenarioRequest[K]) =>
    onChange({ ...value, [k]: v });

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="mb-6 flex items-baseline justify-between">
        <h2 className="h-card">Cargo scenario</h2>
        <span className="eyebrow">input</span>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <label>
          <span className="field-label">Load port — origin</span>
          <select className="field" value={value.origin} onChange={(e) => set("origin", e.target.value)}>
            {loadPorts.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name} · {p.country}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Discharge port — E. Coast India</span>
          <select
            className="field"
            value={value.destination}
            onChange={(e) => set("destination", e.target.value)}
          >
            {dischargePorts.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name} · {p.max_draft_m} m draft
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Commodity</span>
          <select
            className="field"
            value={value.commodity}
            onChange={(e) => set("commodity", e.target.value)}
          >
            {COMMODITIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Campaign volume — tonnes</span>
          <input
            type="number"
            className="field num"
            min={20000}
            step={10000}
            value={value.cargo_volume_t}
            onChange={(e) => set("cargo_volume_t", Number(e.target.value))}
          />
        </label>

        <label>
          <span className="field-label">Contract duration</span>
          <select
            className="field"
            value={value.contract_duration_months}
            onChange={(e) => set("contract_duration_months", Number(e.target.value))}
          >
            {DURATIONS.map((d) => (
              <option key={d} value={d}>
                {d} month{d > 1 ? "s" : ""}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Target laycan month</span>
          <select
            className="field"
            value={value.laycan_month ?? ""}
            onChange={(e) => set("laycan_month", e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Not set</option>
            {MONTH_NAMES.map((m, i) => (
              <option key={m} value={i + 1}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Pin vessel — optional</span>
          <select
            className="field"
            value={value.vessel ?? ""}
            onChange={(e) => set("vessel", e.target.value || null)}
          >
            <option value="">Optimiser chooses</option>
            {vessels.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Forecast horizon</span>
          <select
            className="field"
            value={value.forecast_horizon_days}
            onChange={(e) => set("forecast_horizon_days", Number(e.target.value))}
          >
            {[60, 90, 120, 180].map((d) => (
              <option key={d} value={d}>
                {d} days
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-8 flex items-center gap-4">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Running the desk…" : "Run analysis"}
        </button>
        <span className="meta">
          Forecasting · vessel optimisation · entry timing · idle &amp; risk — one pass
        </span>
      </div>
    </form>
  );
}

export interface PortRef {
  code: string;
  name: string;
  country: string;
  region: string;
  role: string;
  max_draft_m: number;
  max_loa_m: number;
  max_beam_m: number;
  max_dwt: number;
  handling_tpd: number;
  congestion_base_days: number;
  transload: boolean;
  notes: string;
  source: string;
}

export interface VesselRef {
  name: string;
  dwt: number;
  loa: number;
  beam: number;
  scantling_draft: number;
  laden_speed_kn: number;
  geared: boolean;
  typical_tce_usd_day: number;
}

export interface RouteRef {
  id: string;
  lane: string;
  origin: { code: string; name: string; country?: string; region?: string };
  destination: { code: string; name: string; region?: string };
  distance_nm: number;
  canal: string;
  seasonality_profile?: string;
}

export interface Provenance {
  mode: string;
  note: string;
  attempted_sources: string[];
  live_points: { label: string; url: string; value: number; role?: string }[];
  history_start: string;
  history_end: string;
  series_count: number;
  daily_rows: number;
}

export interface ScenarioRequest {
  origin: string;
  destination: string;
  commodity: string;
  cargo_volume_t: number;
  contract_duration_months: number;
  laycan_month: number | null;
  vessel: string | null;
  forecast_horizon_days: number;
}

export interface VesselOption {
  vessel: string;
  feasible: boolean;
  reasons: string[];
  intake_t: number;
  shipments_required: number;
  governing_draft_m: number;
  draft_utilisation_pct: number;
  voyage_days_roundtrip: number;
  freight_usd_per_t: number;
  expected_wait_days: number;
  demurrage_risk_usd_per_t: number;
  delivered_cost_usd_per_t: number;
  total_campaign_cost_usd: number;
  campaign_lead_time_days: number;
  score: number;
}

export interface Forecast {
  route_id: string;
  vessel: string;
  as_of: string;
  latest_rate: number;
  horizon_days: number;
  model: string;
  history: { date: string; rate: number }[];
  forecast: { date: string; mean: number; lo: number; hi: number }[];
  monthly: { month: string; mean: number; lo: number; hi: number }[];
  expected_rate: { next_30d: number; next_60d: number; next_90d: number };
  current_percentile_12m: number;
  seasonal_factor_now: number;
  backtest: {
    folds: number;
    fold_horizon_weeks: number;
    ensemble: { mape: number | null; rmse: number | null; bias: number | null };
    models: Record<string, { mape: number | null; rmse: number | null; bias: number | null }>;
  };
  drivers: Record<string, number | null>;
}

export interface Timing {
  route_id: string;
  vessel: string;
  as_of: string;
  current_rate_usd_t: number;
  annualised_volatility_pct: number;
  forecast_slope_over_contract_pct: number;
  entry_timing: {
    action: "WAIT" | "FIX_NOW";
    window: { from: string; to: string; weeks_out: number };
    expected_saving_usd: number;
    rationale: string;
  };
  charter_structure: {
    recommendation: "SPOT" | "PERIOD";
    contract_duration_months: number;
    spot: { expected_rate_usd_t: number; expected_cost_usd: number; cost_std_usd: number };
    period: {
      indicative_rate_usd_t: number;
      expected_cost_usd: number;
      cost_std_usd: number;
      liquidity_premium_pct: number;
    };
    rationale: string;
  };
  vs_reactive_spot_approach: {
    reactive_expected_cost_usd: number;
    reactive_cost_std_usd: number;
    recommended_expected_cost_usd: number;
    recommended_cost_std_usd: number;
    expected_saving_usd: number;
    expected_saving_pct: number;
    risk_reduction_usd: number;
    flat_rate_reference_cost_usd: number;
    note: string;
  };
}

export interface IdleOutlook {
  route_id: string;
  vessel: string;
  lane: string;
  idle_risk_index: number;
  estimated_idle_days_next_12w: number;
  components: { demand_pressure: number; congestion_pressure: number; monsoon_pressure: number };
  soft_demand_weeks: { week: string; seasonal_factor: number }[];
  discharge_wait_days_now: number;
  discharge_wait_days_year_avg: number;
  alternative_lanes: {
    route_id: string;
    lane: string;
    near_term_demand_factor: number;
    discharge_wait_days: number;
    demand_weight: number;
  }[];
  mitigation: string[];
}

export interface RiskAlert {
  id: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  scope: Record<string, string>;
  message: string;
  recommended_action: string;
  metrics: Record<string, unknown>;
  detected_at: string;
}

export interface ScenarioResponse {
  request: ScenarioRequest;
  resolved: { route_id: string; vessel: string; lane: string; has_market_series: boolean };
  vessel_optimisation: {
    route: RouteRef & { synthesized?: boolean };
    cargo: { commodity: string; volume_t: number; laycan_month: number | null };
    constraints: { load_port: PortRef; discharge_port: PortRef };
    recommendation: {
      vessel: string;
      why: string;
      delivered_cost_usd_per_t: number;
      shipments_required: number;
      estimated_campaign_cost_usd: number;
      potential_saving_vs_worst_feasible_usd: number | null;
    } | null;
    options: VesselOption[];
    bunker_used_usd_t: number;
  };
  forecast: Forecast | null;
  timing: Timing | null;
  idle_outlook: IdleOutlook | null;
  risk_alerts: {
    scoped: RiskAlert[];
    all_count: number;
    severity_counts: Record<string, number>;
  };
}

export interface MarketSnapshot {
  as_of: string;
  vlsfo_usd_t: number;
  vlsfo_change_30d_pct: number;
  tce_usd_day: Record<string, number>;
  congestion_days: Record<string, number>;
  rates: { route_id: string; lane: string; vessel: string; rate_usd_t: number; change_30d_pct: number | null }[];
}

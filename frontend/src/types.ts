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
  data_sources: Record<string, string>;
  snapshot_date: string | null;
  refreshing: boolean;
  weather_ports: string[];
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
  weather_delay_days: number;
  demurrage_risk_usd_per_t: number;
  delivered_cost_usd_per_t: number;
  total_campaign_cost_usd: number;
  campaign_lead_time_days: number;
  co2_kt_campaign: number;
  co2_g_per_t_nm: number;
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
    ensemble_weight_holt_winters: number;
    models: Record<string, { mape: number | null; rmse: number | null; bias: number | null }>;
    baselines: Record<string, { mape: number | null; rmse: number | null; bias: number | null }>;
    skill_vs_random_walk_pct: number | null;
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

export interface StrategyStat {
  avg_usd_t: number;
  volatility_usd_t: number;
  worst_usd_t: number;
}

export interface DecisionBacktestSummary {
  timed_vs_spot_cost_pct: number;
  timed_vs_spot_volatility_pct: number;
  period_vs_spot_volatility_pct: number;
  worst_period_spot_usd_t: number;
  worst_period_timed_usd_t: number;
  max_spike_avoided_usd_t: number;
  period_locks: number;
  spot_periods: number;
  timely_locks: number;
}

export interface DecisionBacktest {
  route_id: string;
  vessel: string;
  contract_months: number;
  decision_points: number;
  limited_history?: boolean;
  note?: string | null;
  curve: {
    date: string;
    choice: "SPOT" | "PERIOD";
    spot: number;
    period: number;
    timed: number;
    spot_cum: number;
    period_cum: number;
    timed_cum: number;
  }[];
  strategies: {
    always_spot: StrategyStat;
    always_period: StrategyStat;
    timed_cover: StrategyStat;
  };
  summary: DecisionBacktestSummary;
}

export interface Emissions {
  recommended_kt: number;
  recommended_g_per_t_nm: number;
  greenest_feasible: string;
  recommended_vs_greenest_pct: number;
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
    robustness: Record<string, number>;
    emissions: Emissions | null;
    bunker_used_usd_t: number;
  };
  forecast: Forecast | null;
  timing: Timing | null;
  idle_outlook: IdleOutlook | null;
  decision_backtest: {
    strategies: DecisionBacktest["strategies"];
    summary: DecisionBacktestSummary;
    decision_points: number;
    limited_history?: boolean;
    note?: string | null;
  } | null;
  weather: { expected_delay_days_16d: number; high_wind_days: number; heavy_rain_days: number } | null;
  risk_alerts: {
    scoped: RiskAlert[];
    all_count: number;
    severity_counts: Record<string, number>;
  };
}

export interface RequirementItem {
  origin: string;
  destination: string;
  commodity?: string;
  tonnes: number;
  laycan_month?: number | null;
}

export interface PlanRequest {
  requirements: RequirementItem[];
  horizon_months: number;
}

export interface PlanResponse {
  horizon_months: number;
  lanes: {
    route_id: string;
    lane: string;
    commodity: string;
    tonnes: number;
    vessel: string;
    period_cover_pct: number;
    spot_pct: number;
    period_rate_usd_t: number;
    expected_spot_usd_t: number;
    forecast_slope_pct: number;
    plan_cost_usd: number;
    all_spot_cost_usd: number;
    saving_usd: number;
    co2_kt: number;
  }[];
  totals: {
    plan_cost_usd: number;
    all_spot_cost_usd: number;
    expected_saving_usd: number;
    expected_saving_pct: number;
    cost_risk_reduction_usd: number;
    total_co2_kt: number;
    tonnes: number;
  };
}

// ---- Phase 3: live map ---------------------------------------------------- //
export interface MapPort {
  code: string;
  name: string;
  lat: number;
  lon: number;
  basin: string | null;
  country: string | null;
  curated: boolean;
}

export interface MapPortsResponse {
  enabled: boolean;
  backend: string;
  count: number;
  ports: MapPort[];
}

export interface MapVessel {
  mmsi: number;
  name: string | null;
  type: string | null;
  lat: number;
  lon: number;
  sog_kn: number | null;
  cog_deg: number | null;
  heading_deg: number | null;
  nav_status: string | null;
  source: "ais" | "estimated";
  ts: string | null;
  destination: string | null;
}

export interface MapVesselsResponse {
  enabled: boolean;
  generated_at: string | null;
  count?: number;
  vessels: MapVessel[];
}

export interface MapVoyage {
  status: string;
  origin_code: string | null;
  dest_code: string | null;
  dest_raw: string | null;
  departure_ts: string | null;
  eta_ts: string | null;
  confidence: number | null;
}

export interface MapVesselDetail {
  enabled: boolean;
  mmsi?: number;
  vessel?: {
    mmsi: number;
    name: string | null;
    imo: number | null;
    type: string | null;
    loa_m: number | null;
    beam_m: number | null;
    draft_m: number | null;
    destination: string | null;
    eta_raw: string | null;
    nav_status: string | null;
  };
  track?: { lat: number; lon: number; ts: string | null; sog_kn: number | null; source: string }[];
  latest?: { lat: number; lon: number; ts: string | null; sog_kn: number | null; source: string } | null;
  voyage?: MapVoyage | null;
}

export interface MapSummary {
  enabled: boolean;
  ports: number;
  vessels: number;
  observed: number;
  estimated: number;
  active_voyages: number;
  last_sample_at: string | null;
}

export interface MarketSnapshot {
  as_of: string;
  vlsfo_usd_t: number;
  vlsfo_change_30d_pct: number;
  tce_usd_day: Record<string, number>;
  congestion_days: Record<string, number>;
  rates: { route_id: string; lane: string; vessel: string; rate_usd_t: number; change_30d_pct: number | null }[];
}

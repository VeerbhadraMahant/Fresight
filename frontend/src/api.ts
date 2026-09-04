import type {
  DecisionBacktest,
  MapPortsResponse,
  MapSummary,
  MapVesselDetail,
  MapVesselsResponse,
  MarketSnapshot,
  PlanRequest,
  PlanResponse,
  PortHit,
  PortRef,
  PortSearchResponse,
  Provenance,
  RouteRef,
  ScenarioRequest,
  ScenarioResponse,
  Shipment,
  ShipmentCreate,
  ShipmentDetail,
  ShipmentPatch,
  ShipmentsResponse,
  ShipmentValuation,
  VesselRef,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
  const r = await fetch(`${BASE}${path}${qs}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function del(path: string): Promise<void> {
  const r = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`${path} -> ${r.status} ${await r.text()}`);
}

export const api = {
  health: () => get<{ status: string }>("/api/health"),
  ports: () => get<{ discharge_ports: PortRef[]; load_ports: PortRef[] }>("/api/reference/ports"),
  portSearch: (q: string) =>
    get<PortSearchResponse>("/api/reference/ports/search", { q, limit: 24 }),
  resolvePort: (ident: string) => get<PortHit>("/api/reference/port", { ident }),
  vessels: () => get<VesselRef[]>("/api/reference/vessels"),
  routes: () => get<RouteRef[]>("/api/reference/routes"),
  provenance: () => get<Provenance>("/api/reference/market/provenance"),
  snapshot: () => get<MarketSnapshot>("/api/reference/market/snapshot"),
  scenario: (req: ScenarioRequest) => post<ScenarioResponse>("/api/scenario", req),
  decisionBacktest: (route_id: string, vessel: string, contract_months: number) =>
    get<DecisionBacktest>("/api/backtest/decisions", { route_id, vessel, contract_months }),
  plan: (req: PlanRequest) => post<PlanResponse>("/api/plan", req),

  // Phase 3: live map
  mapSummary: () => get<MapSummary>("/api/map/summary"),
  mapPorts: (bbox?: string) =>
    get<MapPortsResponse>("/api/map/ports", bbox ? { bbox, limit: 2500 } : { limit: 1800 }),
  mapVessels: (bbox?: string) =>
    get<MapVesselsResponse>("/api/map/vessels", bbox ? { bbox, limit: 1200 } : { limit: 1200 }),
  mapVessel: (mmsi: number) => get<MapVesselDetail>(`/api/map/vessel/${mmsi}`),

  // Phase D: shipment tracking
  shipments: () => get<ShipmentsResponse>("/api/shipments"),
  shipment: (ref: string) => get<ShipmentDetail>(`/api/shipments/${ref}`),
  createShipment: (body: ShipmentCreate) => post<Shipment>("/api/shipments", body),
  patchShipment: (ref: string, body: ShipmentPatch) =>
    patch<Shipment>(`/api/shipments/${ref}`, body),
  deleteShipment: (ref: string) => del(`/api/shipments/${ref}`),
  revalueShipment: (ref: string) =>
    post<ShipmentValuation>(`/api/shipments/${ref}/revalue`, {}),
};

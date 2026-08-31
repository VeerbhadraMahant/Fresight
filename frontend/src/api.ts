import type {
  MarketSnapshot,
  PortRef,
  Provenance,
  RouteRef,
  ScenarioRequest,
  ScenarioResponse,
  VesselRef,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
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

export const api = {
  health: () => get<{ status: string }>("/api/health"),
  ports: () => get<{ discharge_ports: PortRef[]; load_ports: PortRef[] }>("/api/reference/ports"),
  vessels: () => get<VesselRef[]>("/api/reference/vessels"),
  routes: () => get<RouteRef[]>("/api/reference/routes"),
  provenance: () => get<Provenance>("/api/reference/market/provenance"),
  snapshot: () => get<MarketSnapshot>("/api/reference/market/snapshot"),
  scenario: (req: ScenarioRequest) => post<ScenarioResponse>("/api/scenario", req),
};

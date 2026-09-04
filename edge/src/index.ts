/**
 * Worker entry — routes browser traffic to the single FleetRelay Durable Object.
 *
 *   GET /ws       WebSocket upgrade -> live vessel stream (snapshot + deltas)
 *   GET /health   relay status (viewers, vessels, upstream, key present)
 *   GET /         plain-text hint
 *
 * One global DO instance ("relay") is enough: it is a fan-out hub, not per-user
 * state. Scale later by sharding on bbox if a single instance ever saturates.
 */

import { FleetRelay, type Env } from "./fleet-relay";

export { FleetRelay };

function cors(env: Env, origin: string | null): Record<string, string> {
  const allow = (env.ALLOW_ORIGINS ?? "*").trim();
  const value = allow === "*" || !origin ? "*" : allow.split(",").map((s) => s.trim()).includes(origin) ? origin : allow.split(",")[0];
  return {
    "Access-Control-Allow-Origin": value,
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const headers = cors(env, origin);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });

    if (url.pathname === "/" ) {
      return new Response("FreightSight live-AIS relay. Connect a WebSocket to /ws; status at /health.", {
        headers: { "content-type": "text/plain", ...headers },
      });
    }

    if (url.pathname === "/ws" || url.pathname === "/health") {
      const id = env.FLEET_RELAY.idFromName("relay");
      const stub = env.FLEET_RELAY.get(id);
      const res = await stub.fetch(request);
      if (url.pathname === "/health") {
        const body = await res.text();
        return new Response(body, { status: res.status, headers: { "content-type": "application/json", ...headers } });
      }
      return res; // 101 upgrade passes straight through
    }

    return new Response("not found", { status: 404, headers });
  },
};

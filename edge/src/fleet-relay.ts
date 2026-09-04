/**
 * FleetRelay — one Durable Object instance that fans a single upstream
 * AISStream.io WebSocket out to every browser viewing the live map.
 *
 * Lifecycle (this is the whole point):
 *   • first viewer connects  → open the upstream AIS socket, start an alarm
 *   • frames arrive          → merge into an in-memory fleet map, broadcast deltas
 *   • last viewer disconnects → close the upstream socket, cancel the alarm
 *                               → the DO goes idle and is evicted (zero cost)
 *
 * Client sockets use the WebSocket Hibernation API, so the DO can be evicted
 * from memory between frames without dropping viewers. Per-socket viewport is
 * kept in the socket's hibernation attachment. The fleet map is not persisted —
 * if the DO is evicted it simply refills from the stream within a few seconds.
 */

import { parseFrame, type LiveVessel } from "./ais";

const AIS_URL = "https://stream.aisstream.io/v0/stream";
const ALARM_MS = 30_000;
const UPSTREAM_RETRY_MS = 5_000;

export interface Env {
  FLEET_RELAY: DurableObjectNamespace;
  AISSTREAM_API_KEY?: string;
  AIS_BBOX?: string;
  STALE_MINUTES?: string;
  ALLOW_ORIGINS?: string;
}

type BBox = [number, number, number, number]; // minLat, minLon, maxLat, maxLon

interface SocketMeta {
  bbox?: BBox;
}

function parseBoxes(spec: string | undefined): number[][][] {
  // "minLat,minLon,maxLat,maxLon; ..." -> AISStream's [[[minLat,minLon],[maxLat,maxLon]], ...]
  if (!spec) return [[[-90, -180], [90, 180]]];
  const boxes: number[][][] = [];
  for (const part of spec.split(";")) {
    const n = part.split(",").map((x) => Number(x.trim()));
    if (n.length === 4 && n.every(Number.isFinite)) {
      boxes.push([[n[0], n[1]], [n[2], n[3]]]);
    }
  }
  return boxes.length ? boxes : [[[-90, -180], [90, 180]]];
}

const inBox = (v: LiveVessel, b: BBox | undefined): boolean =>
  !b || (v.lat >= b[0] && v.lat <= b[2] && v.lon >= b[1] && v.lon <= b[3]);

export class FleetRelay implements DurableObject {
  private fleet = new Map<number, LiveVessel>();
  private statics = new Map<number, { name: string | null; type: string | null; destination: string | null }>();
  private upstream: WebSocket | null = null;
  private connecting = false;
  private lastFrameAt = 0;

  constructor(private ctx: DurableObjectState, private env: Env) {
    // If we were evicted while viewers stayed connected, re-open the upstream.
    this.ctx.blockConcurrencyWhile(async () => {
      if (this.ctx.getWebSockets().length > 0) this.ensureUpstream();
    });
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname.endsWith("/health")) {
      return Response.json({
        ok: true,
        viewers: this.ctx.getWebSockets().length,
        vessels: this.fleet.size,
        upstream: this.upstream ? "connected" : "closed",
        last_frame_age_s: this.lastFrameAt ? Math.round((Date.now() - this.lastFrameAt) / 1000) : null,
        bbox: this.env.AIS_BBOX ?? "world",
        has_key: Boolean(this.env.AISSTREAM_API_KEY),
      });
    }

    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected a WebSocket upgrade", { status: 426 });
    }

    const pair = new WebSocketPair();
    const [client, server] = [pair[0], pair[1]];
    this.ctx.acceptWebSocket(server);
    server.serializeAttachment({} satisfies SocketMeta);

    // greet the new viewer with the current fleet, then open upstream if needed
    const snapshot = [...this.fleet.values()];
    server.send(JSON.stringify({ type: "snapshot", ts: new Date().toISOString(), vessels: snapshot }));
    this.ensureUpstream();
    if (this.ctx.getWebSockets().length === 1) await this.ctx.storage.setAlarm(Date.now() + ALARM_MS);

    return new Response(null, { status: 101, webSocket: client });
  }

  // ---- client socket events (hibernation API) --------------------------- //
  webSocketMessage(ws: WebSocket, raw: string | ArrayBuffer): void {
    if (typeof raw !== "string") return;
    try {
      const msg = JSON.parse(raw) as { type?: string; bbox?: BBox };
      if (msg.type === "view" && Array.isArray(msg.bbox) && msg.bbox.length === 4) {
        ws.serializeAttachment({ bbox: msg.bbox } satisfies SocketMeta);
        // immediate refresh for the new viewport
        const inView = [...this.fleet.values()].filter((v) => inBox(v, msg.bbox));
        ws.send(JSON.stringify({ type: "snapshot", ts: new Date().toISOString(), vessels: inView }));
      }
    } catch {
      /* ignore malformed client messages */
    }
    if (this.ctx.getWebSockets().length > 0) this.ensureUpstream();
  }

  webSocketClose(ws: WebSocket): void {
    try {
      ws.close();
    } catch {
      /* already closing */
    }
    this.maybeShutdown();
  }

  webSocketError(): void {
    this.maybeShutdown();
  }

  async alarm(): Promise<void> {
    const viewers = this.ctx.getWebSockets();
    if (viewers.length === 0) {
      this.maybeShutdown();
      return;
    }
    // prune vessels we haven't heard from in STALE_MINUTES
    const staleMs = (Number(this.env.STALE_MINUTES) || 60) * 60_000;
    const cutoff = Date.now() - staleMs;
    const dropped: number[] = [];
    for (const [mmsi, v] of this.fleet) {
      if (new Date(v.ts).getTime() < cutoff) {
        this.fleet.delete(mmsi);
        dropped.push(mmsi);
      }
    }
    const beat = JSON.stringify({
      type: "beat",
      ts: new Date().toISOString(),
      vessels: this.fleet.size,
      upstream: this.upstream ? "connected" : "closed",
      dropped,
    });
    for (const ws of viewers) {
      try {
        ws.send(beat);
      } catch {
        /* socket gone; close event will clean up */
      }
    }
    this.ensureUpstream();
    await this.ctx.storage.setAlarm(Date.now() + ALARM_MS);
  }

  // ---- upstream AIS socket -------------------------------------------- //
  private ensureUpstream(): void {
    if (this.upstream || this.connecting) return;
    const key = this.env.AISSTREAM_API_KEY;
    if (!key) return; // no key -> relay runs but forwards nothing (viewers see REST-only)
    this.connecting = true;

    this.ctx.waitUntil(
      (async () => {
        try {
          const resp = await fetch(AIS_URL, { headers: { Upgrade: "websocket" } });
          const ws = resp.webSocket;
          if (!ws) throw new Error(`no webSocket on upstream response (status ${resp.status})`);
          ws.accept();
          this.upstream = ws;
          this.connecting = false;

          ws.send(
            JSON.stringify({
              APIKey: key,
              BoundingBoxes: parseBoxes(this.env.AIS_BBOX),
              FilterMessageTypes: ["PositionReport", "ShipStaticData"],
            }),
          );

          ws.addEventListener("message", (ev: MessageEvent) => this.onUpstreamFrame(ev.data));
          ws.addEventListener("close", () => this.onUpstreamGone("close"));
          ws.addEventListener("error", () => this.onUpstreamGone("error"));
        } catch (err) {
          this.connecting = false;
          console.log("upstream connect failed:", String(err));
          this.scheduleUpstreamRetry();
        }
      })(),
    );
  }

  private onUpstreamFrame(data: unknown): void {
    let msg: unknown;
    try {
      msg = JSON.parse(typeof data === "string" ? data : new TextDecoder().decode(data as ArrayBuffer));
    } catch {
      return;
    }
    if (msg && typeof msg === "object" && "error" in (msg as Record<string, unknown>)) {
      console.log("aisstream error frame:", JSON.stringify((msg as Record<string, unknown>).error).slice(0, 200));
      return;
    }
    const parsed = parseFrame(msg);
    if (!parsed) return;
    this.lastFrameAt = Date.now();

    if ("kind" in parsed) {
      this.statics.set(parsed.mmsi, {
        name: parsed.name,
        type: parsed.type,
        destination: parsed.destination,
      });
      const pos = this.fleet.get(parsed.mmsi);
      if (pos) {
        const merged = { ...pos, name: parsed.name ?? pos.name, type: parsed.type ?? pos.type, destination: parsed.destination ?? pos.destination };
        this.fleet.set(parsed.mmsi, merged);
        this.broadcast(merged);
      }
      return;
    }

    const st = this.statics.get(parsed.mmsi);
    const v: LiveVessel = st
      ? { ...parsed, name: st.name ?? parsed.name, type: st.type, destination: st.destination }
      : parsed;
    this.fleet.set(v.mmsi, v);
    this.broadcast(v);
  }

  private onUpstreamGone(why: string): void {
    console.log("upstream gone:", why);
    this.upstream = null;
    this.connecting = false;
    if (this.ctx.getWebSockets().length > 0) this.scheduleUpstreamRetry();
  }

  private scheduleUpstreamRetry(): void {
    this.ctx.waitUntil(
      new Promise<void>((r) => setTimeout(r, UPSTREAM_RETRY_MS)).then(() => {
        if (this.ctx.getWebSockets().length > 0) this.ensureUpstream();
      }),
    );
  }

  private broadcast(v: LiveVessel): void {
    const frame = JSON.stringify({ type: "upd", v });
    for (const ws of this.ctx.getWebSockets()) {
      const meta = (ws.deserializeAttachment() ?? {}) as SocketMeta;
      if (!inBox(v, meta.bbox)) continue;
      try {
        ws.send(frame);
      } catch {
        /* socket gone */
      }
    }
  }

  private maybeShutdown(): void {
    if (this.ctx.getWebSockets().length > 0) return;
    if (this.upstream) {
      try {
        this.upstream.close(1000, "no viewers");
      } catch {
        /* already closed */
      }
      this.upstream = null;
    }
    this.connecting = false;
    this.fleet.clear();
    this.statics.clear();
    this.ctx.waitUntil(this.ctx.storage.deleteAlarm());
  }
}

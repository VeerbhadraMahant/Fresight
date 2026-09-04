import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MapVessel } from "../types";

/**
 * Live vessel stream from the Cloudflare relay (edge/). When VITE_LIVE_WS_URL is
 * set the map gets AIS positions pushed in real time; when it is not, this hook
 * is inert and the map falls back to REST polling only.
 *
 * Wire protocol (see edge/src/fleet-relay.ts):
 *   ->  {type:"view", bbox:[minLat,minLon,maxLat,maxLon]}
 *   <-  {type:"snapshot", vessels:[LiveVessel]}
 *   <-  {type:"upd", v:LiveVessel}
 *   <-  {type:"beat", dropped:[mmsi], vessels:n, upstream:"connected"|"closed"}
 */

const WS_URL: string | undefined = import.meta.env.VITE_LIVE_WS_URL;

type LiveVessel = Omit<MapVessel, "source"> & { source: "ais" };

interface Beat {
  upstream: "connected" | "closed";
  vessels: number;
  ts: string;
}

export interface LiveFleet {
  enabled: boolean;
  connected: boolean;
  vessels: Map<number, MapVessel>;
  beat: Beat | null;
  setView: (bbox: [number, number, number, number]) => void;
}

export function useLiveFleet(): LiveFleet {
  const [connected, setConnected] = useState(false);
  const [beat, setBeat] = useState<Beat | null>(null);
  const [vessels, setVessels] = useState<Map<number, MapVessel>>(new Map());
  const wsRef = useRef<WebSocket | null>(null);
  const viewRef = useRef<[number, number, number, number] | null>(null);
  const retryRef = useRef(0);
  const deadRef = useRef(false);

  const ingest = useCallback((raw: string) => {
    let m: Record<string, unknown>;
    try {
      m = JSON.parse(raw);
    } catch {
      return;
    }
    if (m.type === "snapshot") {
      const next = new Map<number, MapVessel>();
      for (const v of (m.vessels as LiveVessel[]) ?? []) next.set(v.mmsi, v);
      setVessels(next);
    } else if (m.type === "upd") {
      const v = m.v as LiveVessel;
      setVessels((cur) => {
        const next = new Map(cur);
        next.set(v.mmsi, v);
        return next;
      });
    } else if (m.type === "beat") {
      setBeat({ upstream: m.upstream as Beat["upstream"], vessels: Number(m.vessels), ts: String(m.ts) });
      const dropped = (m.dropped as number[]) ?? [];
      if (dropped.length) {
        setVessels((cur) => {
          const next = new Map(cur);
          for (const mmsi of dropped) next.delete(mmsi);
          return next;
        });
      }
    }
  }, []);

  useEffect(() => {
    if (!WS_URL) return;
    deadRef.current = false;

    const connect = () => {
      if (deadRef.current) return;
      let ws: WebSocket;
      try {
        ws = new WebSocket(WS_URL);
      } catch {
        schedule();
        return;
      }
      wsRef.current = ws;
      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
        if (viewRef.current) ws.send(JSON.stringify({ type: "view", bbox: viewRef.current }));
      };
      ws.onmessage = (ev) => ingest(typeof ev.data === "string" ? ev.data : "");
      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        schedule();
      };
      ws.onerror = () => ws.close();
    };

    const schedule = () => {
      if (deadRef.current) return;
      const wait = Math.min(30_000, 1_000 * 2 ** retryRef.current++);
      window.setTimeout(connect, wait);
    };

    connect();
    return () => {
      deadRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [ingest]);

  const setView = useCallback((bbox: [number, number, number, number]) => {
    viewRef.current = bbox;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "view", bbox }));
    }
  }, []);

  return useMemo(
    () => ({ enabled: Boolean(WS_URL), connected, vessels, beat, setView }),
    [connected, vessels, beat, setView],
  );
}

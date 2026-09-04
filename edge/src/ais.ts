/**
 * AISStream.io frame parser — a direct port of the pure half of the backend's
 * app/live/ais.py, so the edge relay and the Python worker agree on what a
 * "clean" position is (same sentinel handling: Sog 102.3, Cog 360, heading 511,
 * lat/lon 91/181 all mean "not available").
 */

export interface LiveVessel {
  mmsi: number;
  name: string | null;
  type: string | null;
  lat: number;
  lon: number;
  sog_kn: number | null;
  cog_deg: number | null;
  heading_deg: number | null;
  nav_status: string | null;
  destination: string | null;
  source: "ais";
  ts: string; // ISO 8601
}

const NAV_STATUS: Record<number, string> = {
  0: "under way (engine)",
  1: "at anchor",
  2: "not under command",
  3: "restricted manoeuvrability",
  4: "constrained by draught",
  5: "moored",
  6: "aground",
  7: "engaged in fishing",
  8: "under way (sailing)",
};

const numOrNull = (v: unknown): number | null => {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
};

const sog = (v: unknown): number | null => {
  const n = numOrNull(v);
  return n === null || n < 0 || n >= 102.3 ? null : n;
};
const cog = (v: unknown): number | null => {
  const n = numOrNull(v);
  return n === null || n < 0 || n >= 360 ? null : n;
};
const heading = (v: unknown): number | null => {
  const n = numOrNull(v);
  return n === null || n < 0 || n >= 511 ? null : n % 360;
};

const clean = (s: unknown): string | null => {
  if (typeof s !== "string") return null;
  const t = s.replace(/@/g, "").trim();
  return t || null;
};

/** "2026-09-03 10:11:12.3 +0000 UTC" -> ISO; falls back to now on garbage. */
const metaTs = (meta: Record<string, unknown>): string => {
  const raw = typeof meta?.time_utc === "string" ? meta.time_utc : "";
  const head = raw.slice(0, 19).replace(" ", "T");
  const d = new Date(head + "Z");
  return Number.isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
};

const isDryBulk = (t: number | null): boolean => t !== null && t >= 70 && t <= 79;

export interface StaticUpdate {
  kind: "static";
  mmsi: number;
  name: string | null;
  type: string | null;
  destination: string | null;
}

/** Returns a LiveVessel (position), a StaticUpdate, or null (uninteresting frame). */
export function parseFrame(msg: unknown): LiveVessel | StaticUpdate | null {
  if (!msg || typeof msg !== "object") return null;
  const m = msg as Record<string, unknown>;
  const mtype = m.MessageType as string | undefined;
  const meta = (m.MetaData ?? {}) as Record<string, unknown>;
  const body = ((m.Message ?? {}) as Record<string, unknown>)[mtype ?? ""] as
    | Record<string, unknown>
    | undefined;
  if (!body) return null;

  const mmsi = numOrNull(meta.MMSI ?? body.UserID);
  if (mmsi === null) return null;

  if (mtype === "PositionReport") {
    const lat = numOrNull(body.Latitude);
    const lon = numOrNull(body.Longitude);
    if (lat === null || lon === null) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    return {
      mmsi,
      name: clean(meta.ShipName),
      type: null,
      lat,
      lon,
      sog_kn: sog(body.Sog),
      cog_deg: cog(body.Cog),
      heading_deg: heading(body.TrueHeading),
      nav_status: NAV_STATUS[Number(body.NavigationalStatus)] ?? null,
      destination: null,
      source: "ais",
      ts: metaTs(meta),
    };
  }

  if (mtype === "ShipStaticData") {
    const shipType = numOrNull(body.Type ?? body.ShipType);
    return {
      kind: "static",
      mmsi,
      name: clean(body.Name) ?? clean(meta.ShipName),
      type: shipType === null ? null : isDryBulk(shipType) ? "dry_bulk" : `type_${shipType}`,
      destination: clean(body.Destination),
    };
  }

  return null;
}

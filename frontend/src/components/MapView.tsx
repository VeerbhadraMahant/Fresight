import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  useMapEvents,
} from "react-leaflet";
import { api } from "../api";
import { useLiveFleet } from "../lib/liveFleet";
import type { MapPort, MapSummary, MapVessel, MapVesselDetail } from "../types";

const START_CENTER: [number, number] = [18, 60];
const START_ZOOM = 3;
const VESSEL_POLL_MS = 45_000;
const MOVE_DEBOUNCE_MS = 250;
const R_NM = 3440.065;

const wrapLng = (x: number) => (((x + 180) % 360) + 360) % 360 - 180;

/** Point `nm` nautical miles from (lat,lon) along compass bearing `cog`. */
function projectAhead(lat: number, lon: number, cog: number, nm: number): [number, number] {
  const br = (cog * Math.PI) / 180;
  const dLat = ((nm / R_NM) * Math.cos(br) * 180) / Math.PI;
  const dLon =
    ((nm / R_NM) * Math.sin(br) * 180) / Math.PI / Math.cos((lat * Math.PI) / 180);
  return [lat + dLat, lon + dLon];
}

// amber = observed AIS · slate = dead-reckoned estimate
const SRC_COLOR: Record<string, string> = { ais: "#b45309", estimated: "#64748b" };

// The map wraps infinitely, so getWest()/getEast() can run past ±180 or span
// several worlds. Collapse that to a single [-180,180] query the API understands.
function bboxString(b: L.LatLngBounds): string {
  const s = b.getSouth();
  const n = b.getNorth();
  let w = b.getWest();
  let e = b.getEast();
  if (e - w >= 359) {
    w = -180;
    e = 180; // whole world (or more) in view
  } else {
    w = wrapLng(w);
    e = wrapLng(e);
  }
  return [w, s, e, n].map((x) => x.toFixed(3)).join(",");
}

/** Small rotated chevron; rotation follows heading, else course, else 0. */
function vesselIcon(v: MapVessel): L.DivIcon {
  const rot = v.heading_deg ?? v.cog_deg ?? 0;
  const fill = SRC_COLOR[v.source] ?? "#b45309";
  const dashed = v.source === "estimated";
  return L.divIcon({
    className: "",
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    html:
      `<svg width="16" height="16" viewBox="0 0 16 16" style="transform:rotate(${rot}deg)">` +
      `<path d="M8 1 L13 14 L8 11 L3 14 Z" fill="${fill}" ` +
      `stroke="#1c1917" stroke-width="0.8" ${dashed ? 'stroke-dasharray="2 1.5"' : ""}/></svg>`,
  });
}

function MapEvents({ onMove }: { onMove: (b: L.LatLngBounds, zoom: number) => void }) {
  const map = useMapEvents({
    moveend: () => onMove(map.getBounds(), map.getZoom()),
    load: () => onMove(map.getBounds(), map.getZoom()),
  });
  useEffect(() => {
    onMove(map.getBounds(), map.getZoom());
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}

export function MapView() {
  const [summary, setSummary] = useState<MapSummary | null>(null);
  const [ports, setPorts] = useState<MapPort[]>([]);
  const [vessels, setVessels] = useState<MapVessel[]>([]);
  const [vesselsEnabled, setVesselsEnabled] = useState<boolean | null>(null);
  const [bounds, setBounds] = useState<L.LatLngBounds | null>(null);
  const [zoom, setZoom] = useState(START_ZOOM);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<MapVesselDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const bboxRef = useRef<string | null>(null);
  const moveTimer = useRef<number | undefined>(undefined);
  const live = useLiveFleet();

  // ports never change -> fetch the whole set once, filter client-side
  useEffect(() => {
    api.mapSummary().then(setSummary).catch(() => undefined);
    api
      .mapPorts()
      .then((p) => setPorts(p.ports))
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  const fetchVessels = useCallback((bbox: string) => {
    api
      .mapVessels(bbox)
      .then((v) => {
        setVessels(v.vessels);
        setVesselsEnabled(v.enabled);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  const onMove = useCallback(
    (b: L.LatLngBounds, z: number) => {
      setZoom(z);
      setBounds(b);
      const s = bboxString(b);
      bboxRef.current = s;
      // push the viewport to the live relay so it only streams what's on screen
      live.setView([b.getSouth(), wrapLng(b.getWest()), b.getNorth(), wrapLng(b.getEast())]);
      window.clearTimeout(moveTimer.current);
      moveTimer.current = window.setTimeout(() => fetchVessels(s), MOVE_DEBOUNCE_MS);
    },
    [fetchVessels, live],
  );

  // re-poll vessels on the current viewport, but only while the tab is visible
  useEffect(() => {
    const id = window.setInterval(() => {
      if (bboxRef.current && !document.hidden) fetchVessels(bboxRef.current);
    }, VESSEL_POLL_MS);
    return () => window.clearInterval(id);
  }, [fetchVessels]);

  // load detail for the selected vessel
  useEffect(() => {
    if (selected == null) {
      setDetail(null);
      return;
    }
    api.mapVessel(selected).then(setDetail).catch(() => setDetail(null));
  }, [selected]);

  // client-side: curated ports always, the rest only when zoomed in, and only
  // those inside the current viewport (cap so a wide low-zoom view stays light)
  const shownPorts = useMemo(() => {
    const inView = (p: MapPort) =>
      !bounds || bounds.contains([p.lat, p.lon] as L.LatLngExpression);
    const base = zoom >= 5 ? ports : ports.filter((p) => p.curated);
    const out = base.filter(inView);
    return out.length > 600 ? out.slice(0, 600) : out;
  }, [ports, zoom, bounds]);

  const track = useMemo<[number, number][]>(
    () => (detail?.track ?? []).map((t) => [t.lat, t.lon] as [number, number]),
    [detail],
  );

  // live relay wins per-MMSI (it's seconds-fresh); REST fills the rest
  const renderVessels = useMemo<MapVessel[]>(() => {
    if (!live.enabled || live.vessels.size === 0) return vessels;
    const m = new Map<number, MapVessel>(vessels.map((v) => [v.mmsi, v]));
    for (const [mmsi, lv] of live.vessels) m.set(mmsi, lv);
    return [...m.values()];
  }, [vessels, live.enabled, live.vessels]);

  const selectedVessel = renderVessels.find((v) => v.mmsi === selected) ?? null;

  // straight-line hint to the resolved AIS destination port, when we have one
  const courseHint = useMemo<[number, number][] | null>(() => {
    const dst = detail?.voyage?.dest_code;
    if (!dst || !detail?.latest) return null;
    const port = ports.find((p) => p.code === dst);
    if (!port) return null;
    return [
      [detail.latest.lat, detail.latest.lon],
      [port.lat, port.lon],
    ];
  }, [detail, ports]);

  // where the selected vessel is heading right now: a ray along its course,
  // ~12 h ahead at current speed (min 60 nm so it's visible when slow/stopped)
  const courseRay = useMemo<[number, number][] | null>(() => {
    const v = selectedVessel;
    if (!v || v.cog_deg == null) return null;
    const reach = Math.min(600, Math.max(60, (v.sog_kn ?? 0) * 12));
    return [
      [v.lat, v.lon],
      projectAhead(v.lat, v.lon, v.cog_deg, reach),
    ];
  }, [selectedVessel]);

  return (
    <div className="relative w-full" style={{ height: "calc(100dvh - 5.5rem)" }}>
      <MapContainer
        center={START_CENTER}
        zoom={START_ZOOM}
        minZoom={2}
        worldCopyJump
        preferCanvas
        style={{ height: "100%", width: "100%", background: "#dfe4e8" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapEvents onMove={onMove} />

        {shownPorts.map((p) => (
          <CircleMarker
            key={p.code}
            center={[p.lat, p.lon]}
            radius={p.curated ? 3.5 : 2}
            pathOptions={{
              color: p.curated ? "#0f766e" : "#94a3b8",
              weight: 1,
              fillOpacity: 0.7,
            }}
          >
            <Tooltip>
              {p.name} · {p.code}
              {p.basin ? ` · ${p.basin}` : ""}
            </Tooltip>
          </CircleMarker>
        ))}

        {track.length > 1 && (
          <Polyline positions={track} pathOptions={{ color: "#b45309", weight: 2, opacity: 0.85 }} />
        )}
        {courseRay && (
          <Polyline
            positions={courseRay}
            pathOptions={{ color: "#1d4ed8", weight: 2, dashArray: "2 5", opacity: 0.9 }}
          />
        )}
        {courseHint && (
          <Polyline
            positions={courseHint}
            pathOptions={{ color: "#0f766e", weight: 1.5, dashArray: "6 6", opacity: 0.7 }}
          />
        )}

        {/* fleet: canvas circles — cheap for ~1k points */}
        {renderVessels.map((v) => (
          <CircleMarker
            key={v.mmsi}
            center={[v.lat, v.lon]}
            radius={v.mmsi === selected ? 6 : 3.5}
            pathOptions={{
              color: v.mmsi === selected ? "#1c1917" : (SRC_COLOR[v.source] ?? "#b45309"),
              weight: v.mmsi === selected ? 2 : 1,
              fillColor: SRC_COLOR[v.source] ?? "#b45309",
              fillOpacity: v.source === "estimated" ? 0.45 : 0.9,
            }}
            eventHandlers={{ click: () => setSelected(v.mmsi) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              {v.name ?? `MMSI ${v.mmsi}`}
              {v.sog_kn != null ? ` · ${v.sog_kn.toFixed(1)} kn` : ""}
              {v.source === "estimated" ? " · est." : ""}
            </Tooltip>
          </CircleMarker>
        ))}

        {/* heading chevron only for the selected vessel (one DOM node) */}
        {selectedVessel && (
          <Marker
            position={[selectedVessel.lat, selectedVessel.lon]}
            icon={vesselIcon(selectedVessel)}
            interactive={false}
          />
        )}
      </MapContainer>

      {/* legend + counters */}
      <div className="pointer-events-none absolute left-3 top-3 z-[1000] max-w-[300px] space-y-2">
        <div
          className="pointer-events-auto rounded-md border border-mist bg-white px-3 py-2 font-sans text-[12px] text-graphite"
          style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.16)" }}
        >
          <div className="flex items-center gap-2">
            <span className="font-display text-[13px]">Live vessel map</span>
            {live.enabled && (
              <span
                className="rounded-pill px-1.5 py-0.5 font-sans text-[10px]"
                style={{
                  background: live.connected ? "#e6efe6" : "#f5f5f5",
                  color: live.connected ? "#2f6b31" : "#828282",
                }}
                title={
                  live.beat
                    ? `relay upstream ${live.beat.upstream} · ${live.beat.vessels} vessels`
                    : "connecting to live relay…"
                }
              >
                {live.connected ? "● streaming" : "○ relay offline"}
              </span>
            )}
          </div>
          <div className="mt-1 text-slate">
            {vesselsEnabled === false && !live.connected ? (
              <span className="text-ember">
                Vessel feed off — the API is running without a database
                (<code>DATABASE_URL</code>). Ports &amp; sea lanes only.
              </span>
            ) : renderVessels.length === 0 && !live.connected ? (
              <span className="text-ember">
                DB connected but 0 vessels here — pan out, or run{" "}
                <code>python -m worker.ingest</code> to sample AIS.
              </span>
            ) : (
              `${renderVessels.length} vessels in view` +
              (live.connected
                ? " · live"
                : summary?.last_sample_at
                  ? ` · sampled ${new Date(summary.last_sample_at).toUTCString().slice(17, 22)} UTC`
                  : "")
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-slate">
            <span>
              <span style={{ color: "#b45309" }}>▲</span> AIS
            </span>
            <span>
              <span style={{ color: "#64748b" }}>▲</span> estimated
            </span>
            <span>
              <span style={{ color: "#0f766e" }}>●</span> port
            </span>
            <span>
              <span style={{ color: "#1d4ed8" }}>┈</span> course (12 h)
            </span>
          </div>
          <div className="mt-1 text-slate">Click a vessel for its track &amp; heading.</div>
        </div>
        {err && (
          <div
          className="pointer-events-auto rounded-md border border-mist bg-white px-3 py-2 font-sans text-[12px] text-graphite"
          style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.16)" }}
        >
            Map data error: {err}
          </div>
        )}
      </div>

      {/* selected-vessel detail */}
      {selected != null && (
        <div
          className="absolute right-3 top-3 z-[1000] w-[320px] rounded-md border border-mist bg-white p-4 font-sans text-[13px] text-graphite"
          style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.22)" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="font-display text-[15px] leading-tight">
              {detail?.vessel?.name ?? selectedVessel?.name ?? `MMSI ${selected}`}
            </div>
            <button
              type="button"
              className="link text-[12px]"
              onClick={() => setSelected(null)}
            >
              close
            </button>
          </div>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-slate">
            <dt>MMSI</dt>
            <dd className="num text-graphite">{selected}</dd>
            {detail?.vessel?.imo ? (
              <>
                <dt>IMO</dt>
                <dd className="num text-graphite">{detail.vessel.imo}</dd>
              </>
            ) : null}
            {detail?.vessel?.type ? (
              <>
                <dt>Type</dt>
                <dd className="text-graphite">{detail.vessel.type}</dd>
              </>
            ) : null}
            {selectedVessel?.sog_kn != null ? (
              <>
                <dt>Speed</dt>
                <dd className="num text-graphite">
                  {selectedVessel.sog_kn.toFixed(1)} kn
                  {selectedVessel.cog_deg != null ? ` · ${Math.round(selectedVessel.cog_deg)}°` : ""}
                </dd>
              </>
            ) : null}
            {(detail?.vessel?.nav_status ?? selectedVessel?.nav_status) ? (
              <>
                <dt>Status</dt>
                <dd className="text-graphite">
                  {detail?.vessel?.nav_status ?? selectedVessel?.nav_status}
                </dd>
              </>
            ) : null}
            {detail?.vessel?.draft_m ? (
              <>
                <dt>Draft</dt>
                <dd className="num text-graphite">{detail.vessel.draft_m} m</dd>
              </>
            ) : null}
            {(detail?.vessel?.destination ?? selectedVessel?.destination) ? (
              <>
                <dt>Dest (AIS)</dt>
                <dd className="text-graphite">
                  {detail?.vessel?.destination ?? selectedVessel?.destination}
                  {detail?.vessel?.eta_raw ? ` · ETA ${detail.vessel.eta_raw}` : ""}
                </dd>
              </>
            ) : null}
          </dl>

          {detail?.voyage && (
            <div className="mt-3 border-t border-mist pt-2 text-slate">
              <div className="font-display text-[12px] text-graphite">Inferred voyage</div>
              <div className="mt-1">
                {detail.voyage.origin_code ?? "?"} → {detail.voyage.dest_code ?? detail.voyage.dest_raw ?? "?"}
                {" · "}
                {detail.voyage.status}
                {detail.voyage.confidence != null
                  ? ` · conf ${(detail.voyage.confidence * 100).toFixed(0)}%`
                  : ""}
              </div>
            </div>
          )}

          <div className="mt-2 text-[11px] text-slate">
            {(detail?.track?.length ?? 0) > 1
              ? `Amber = ${detail!.track!.length} AIS fixes, last 72 h. `
              : "Track builds as the AIS worker samples (every ~15 min). "}
            Blue dotted = current course, ~12 h ahead. Dashed teal = straight line to the AIS
            destination (not a routed path).
          </div>
          {detail && !detail.enabled && (
            <div className="mt-2 text-[11px] text-slate">
              Detail unavailable — the API has no database configured yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

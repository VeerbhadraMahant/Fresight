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
import type { MapPort, MapSummary, MapVessel, MapVesselDetail } from "../types";

const START_CENTER: [number, number] = [18, 60];
const START_ZOOM = 3;
const VESSEL_POLL_MS = 45_000;

// amber = observed AIS · slate = dead-reckoned estimate
const SRC_COLOR: Record<string, string> = { ais: "#b45309", estimated: "#64748b" };

function bboxString(b: L.LatLngBounds): string {
  return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((n) => n.toFixed(3)).join(",");
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
  const [zoom, setZoom] = useState(START_ZOOM);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<MapVesselDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const bboxRef = useRef<string | null>(null);

  useEffect(() => {
    api.mapSummary().then(setSummary).catch(() => undefined);
  }, []);

  const refresh = useCallback(async (bbox: string) => {
    try {
      const [p, v] = await Promise.all([api.mapPorts(bbox), api.mapVessels(bbox)]);
      setPorts(p.ports);
      setVessels(v.vessels);
      setVesselsEnabled(v.enabled);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const onMove = useCallback(
    (b: L.LatLngBounds, z: number) => {
      setZoom(z);
      const s = bboxString(b);
      bboxRef.current = s;
      void refresh(s);
    },
    [refresh],
  );

  // poll vessels on the current viewport
  useEffect(() => {
    const id = setInterval(() => {
      if (bboxRef.current) {
        api
          .mapVessels(bboxRef.current)
          .then((v) => {
            setVessels(v.vessels);
            setVesselsEnabled(v.enabled);
          })
          .catch(() => undefined);
      }
    }, VESSEL_POLL_MS);
    return () => clearInterval(id);
  }, []);

  // load detail for the selected vessel
  useEffect(() => {
    if (selected == null) {
      setDetail(null);
      return;
    }
    api.mapVessel(selected).then(setDetail).catch(() => setDetail(null));
  }, [selected]);

  const shownPorts = useMemo(
    () => (zoom >= 5 ? ports : ports.filter((p) => p.curated)),
    [ports, zoom],
  );

  const track = useMemo<[number, number][]>(
    () => (detail?.track ?? []).map((t) => [t.lat, t.lon] as [number, number]),
    [detail],
  );

  const selectedVessel = vessels.find((v) => v.mmsi === selected) ?? null;
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

  return (
    <div className="relative w-full" style={{ height: "calc(100dvh - 5.5rem)" }}>
      <MapContainer
        center={START_CENTER}
        zoom={START_ZOOM}
        minZoom={2}
        worldCopyJump
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
          <Polyline positions={track} pathOptions={{ color: "#b45309", weight: 2, opacity: 0.8 }} />
        )}
        {courseHint && (
          <Polyline
            positions={courseHint}
            pathOptions={{ color: "#0f766e", weight: 1.5, dashArray: "6 6", opacity: 0.7 }}
          />
        )}

        {vessels.map((v) => (
          <Marker
            key={v.mmsi}
            position={[v.lat, v.lon]}
            icon={vesselIcon(v)}
            eventHandlers={{ click: () => setSelected(v.mmsi) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              {v.name ?? `MMSI ${v.mmsi}`}
              {v.sog_kn != null ? ` · ${v.sog_kn.toFixed(1)} kn` : ""}
              {v.source === "estimated" ? " · est." : ""}
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>

      {/* legend + counters */}
      <div className="pointer-events-none absolute left-3 top-3 z-[1000] max-w-[300px] space-y-2">
        <div className="pointer-events-auto rounded-md border border-mist bg-canvas/95 px-3 py-2 font-sans text-[12px] text-graphite shadow-sm">
          <div className="font-display text-[13px]">Live vessel map</div>
          <div className="mt-1 text-slate">
            {vesselsEnabled === false
              ? "Vessel feed not activated — showing world ports & sea lanes."
              : `${vessels.length} vessels in view` +
                (summary?.last_sample_at
                  ? ` · sampled ${new Date(summary.last_sample_at).toUTCString().slice(17, 22)} UTC`
                  : "")}
          </div>
          <div className="mt-1.5 flex items-center gap-3 text-slate">
            <span>
              <span style={{ color: "#b45309" }}>▲</span> AIS
            </span>
            <span>
              <span style={{ color: "#64748b" }}>▲</span> estimated
            </span>
            <span>
              <span style={{ color: "#0f766e" }}>●</span> port
            </span>
          </div>
        </div>
        {err && (
          <div className="pointer-events-auto rounded-md border border-mist bg-canvas/95 px-3 py-2 font-sans text-[12px] text-graphite shadow-sm">
            Map data error: {err}
          </div>
        )}
      </div>

      {/* selected-vessel detail */}
      {selected != null && (
        <div className="absolute right-3 top-3 z-[1000] w-[320px] rounded-md border border-mist bg-canvas/97 p-4 font-sans text-[13px] text-graphite shadow-md">
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

          {detail && (detail.track?.length ?? 0) > 1 && (
            <div className="mt-2 text-[11px] text-slate">
              Track: {detail.track!.length} fixes over the last 72 h (amber). Dashed teal = straight-line
              hint to the AIS destination, not a routed track.
            </div>
          )}
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

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type {
  Shipment,
  ShipmentCreate,
  ShipmentDetail,
  ShipmentStatus,
  VesselRef,
} from "../types";
import { C } from "../lib/theme";
import { num, pct, usd, usdCompact } from "../lib/format";
import { PortPicker } from "./PortPicker";

const STATUSES: ShipmentStatus[] = ["planned", "in_transit", "arrived", "cancelled"];
const COMMODITIES = ["Thermal Coal", "Coking Coal", "Iron Ore", "Bauxite", "Limestone"];

const STATUS_STYLE: Record<ShipmentStatus, string> = {
  planned: "bg-fog text-steel",
  in_transit: "bg-graphite text-canvas",
  arrived: "bg-[#e6efe6] text-[#2f6b31]",
  cancelled: "bg-fog text-slate line-through",
};

function relAge(iso: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return "—";
  const m = Math.round(ms / 60000);
  if (m < 60) return `${m} min ago`;
  const h = m / 60;
  if (h < 48) return `${h.toFixed(0)} h ago`;
  return `${(h / 24).toFixed(0)} d ago`;
}

function etaLabel(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const days = (d.getTime() - Date.now()) / 86_400_000;
  return `${d.toUTCString().slice(5, 16)} · ${days > 0 ? `${days.toFixed(1)} d` : "now"}`;
}

// --------------------------------------------------------------------------- //
function NewShipmentForm({
  vessels,
  onCreated,
}: {
  vessels: VesselRef[];
  onCreated: (s: Shipment) => void;
}) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState<ShipmentCreate>({
    origin_code: "AUHPT",
    dest_code: "INPRT",
    commodity: "Iron Ore",
    cargo_t: 160_000,
    vessel_class: "",
    assigned_mmsi: null,
    contract_months: 6,
  });
  const [mmsiText, setMmsiText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const body: ShipmentCreate = {
        ...f,
        vessel_class: f.vessel_class || undefined,
        assigned_mmsi: mmsiText.trim() ? Number(mmsiText.trim()) : undefined,
      };
      const created = await api.createShipment(body);
      onCreated(created);
      setOpen(false);
      setMmsiText("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button type="button" className="btn-ghost w-full justify-center" onClick={() => setOpen(true)}>
        <Plus size={14} strokeWidth={1.5} /> Track a shipment
      </button>
    );
  }

  return (
    <div className="card-tight space-y-3">
      <div className="flex items-center justify-between">
        <span className="eyebrow">new shipment</span>
        <button type="button" className="link text-[12px]" onClick={() => setOpen(false)}>
          cancel
        </button>
      </div>
      <PortPicker label="Load port" value={f.origin_code} onChange={(c) => setF({ ...f, origin_code: c })} />
      <PortPicker
        label="Discharge port"
        value={f.dest_code}
        onChange={(c) => setF({ ...f, dest_code: c })}
        hint="any port worldwide"
      />
      <label className="block">
        <span className="field-label">Commodity</span>
        <select
          className="field"
          value={f.commodity}
          onChange={(e) => setF({ ...f, commodity: e.target.value })}
        >
          {COMMODITIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="field-label">Cargo (t)</span>
          <input
            type="number"
            step={10_000}
            className="field num"
            value={f.cargo_t}
            onChange={(e) => setF({ ...f, cargo_t: Number(e.target.value) })}
          />
        </label>
        <label className="block">
          <span className="field-label">Contract (mo)</span>
          <input
            type="number"
            min={1}
            max={18}
            className="field num"
            value={f.contract_months}
            onChange={(e) => setF({ ...f, contract_months: Number(e.target.value) })}
          />
        </label>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="field-label">Vessel class</span>
          <select
            className="field"
            value={f.vessel_class ?? ""}
            onChange={(e) => setF({ ...f, vessel_class: e.target.value })}
          >
            <option value="">optimiser picks</option>
            {vessels.map((v) => (
              <option key={v.name}>{v.name}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="field-label">Vessel MMSI</span>
          <input
            className="field num"
            placeholder="optional"
            value={mmsiText}
            onChange={(e) => setMmsiText(e.target.value)}
          />
        </label>
      </div>
      {err && <p className="caption text-ember">{err}</p>}
      <button type="button" className="btn w-full justify-center" onClick={submit} disabled={busy}>
        {busy ? "Creating…" : "Create & capture baseline"}
      </button>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function Tile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "up" | "down";
}) {
  return (
    <div className="card-tight">
      <div className="field-label">{label}</div>
      <div
        className="mt-1 font-display text-[22px] tracking-[-0.02em]"
        style={{ color: accent === "up" ? C.ember : accent === "down" ? "#2f6b31" : C.graphite }}
      >
        {value}
      </div>
      {sub && <div className="meta mt-0.5">{sub}</div>}
    </div>
  );
}

function CostHistory({ d }: { d: ShipmentDetail }) {
  const data = d.cost_history
    .filter((p) => p.ts)
    .map((p) => ({
      t: new Date(p.ts as string).getTime(),
      delivered: p.delivered_usd_per_t,
    }));
  if (data.length < 2) {
    return (
      <p className="meta">
        Delivered-cost history builds as the worker re-values this shipment (every ~15 min).{" "}
        {data.length === 1 ? "1 point so far." : "No points yet."}
      </p>
    );
  }
  const base = d.shipment.baseline_usd_per_t ?? undefined;
  return (
    <div style={{ height: 190 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid stroke={C.mist} strokeDasharray="2 4" />
          <XAxis
            dataKey="t"
            type="number"
            domain={["dataMin", "dataMax"]}
            scale="time"
            tickFormatter={(t) => new Date(t).toUTCString().slice(5, 11)}
            tick={{ fontSize: 11, fill: C.slate }}
            stroke={C.mist}
          />
          <YAxis
            width={52}
            tick={{ fontSize: 11, fill: C.slate }}
            stroke={C.mist}
            tickFormatter={(v) => `$${v.toFixed(0)}`}
            domain={["auto", "auto"]}
          />
          <Tooltip
            labelFormatter={(t) => new Date(t as number).toUTCString().slice(5, 22)}
            formatter={(v: number) => [`$${v.toFixed(2)}/t`, "delivered"]}
          />
          {base != null && (
            <ReferenceLine y={base} stroke={C.slate} strokeDasharray="4 4" label={{ value: "baseline", fontSize: 10, fill: C.slate, position: "insideTopRight" }} />
          )}
          <Line type="monotone" dataKey="delivered" stroke={C.ember} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function DetailPanel({
  refId,
  onChanged,
  onDeleted,
}: {
  refId: string;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const [d, setD] = useState<ShipmentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setErr(null);
    api
      .shipment(refId)
      .then(setD)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [refId]);

  useEffect(() => {
    setD(null);
    load();
  }, [load]);

  const setStatus = async (status: ShipmentStatus) => {
    setBusy(true);
    try {
      await api.patchShipment(refId, { status });
      load();
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const revalueNow = async () => {
    setBusy(true);
    try {
      await api.revalueShipment(refId);
      load();
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await api.deleteShipment(refId);
      onDeleted();
    } finally {
      setBusy(false);
    }
  };

  if (err) return <div className="card border-l-2 border-ember"><p className="caption text-graphite">{err}</p></div>;
  if (!d) return <div className="card"><p className="meta">loading…</p></div>;

  const v = d.valuation;
  const s = d.shipment;
  const lv = d.live_vessel;
  const driftUp = (v.drift_usd_per_t ?? 0) > 0.05;
  const driftDown = (v.drift_usd_per_t ?? 0) < -0.05;
  const modelled = d.analysis.route && "synthesized" in d.analysis.route && d.analysis.route.synthesized;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-display text-[18px] tracking-[-0.02em] text-graphite">{s.ref}</span>
            <span className={`rounded-pill px-2 py-0.5 font-sans text-[11px] ${STATUS_STYLE[s.status]}`}>
              {s.status.replace("_", " ")}
            </span>
          </div>
          <div className="meta mt-1">
            {d.analysis.ports.origin?.name ?? s.origin_code} → {d.analysis.ports.destination?.name ?? s.dest_code}
            {" · "}
            {s.commodity} · {num(s.cargo_t)} t · {v.vessel_class}
            {v.shipments_required && v.shipments_required > 1 ? ` · ${v.shipments_required} parcels` : ""}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className="btn-ghost !py-1.5" onClick={revalueNow} disabled={busy}>
            <RefreshCw size={13} strokeWidth={1.5} /> Re-value
          </button>
          <button type="button" className="btn-ghost !py-1.5" onClick={remove} disabled={busy} aria-label="delete">
            <Trash2 size={13} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {modelled && (
        <p className="caption border-l-2 border-ember pl-3 text-graphite">
          No traded benchmark for this lane — delivered cost rides a <em>modelled</em> price history.
          Directional.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile
          label="Delivered now"
          value={`$${v.delivered_usd_per_t.toFixed(2)}/t`}
          sub={
            v.drift_usd_per_t == null
              ? "no baseline"
              : `${v.drift_usd_per_t >= 0 ? "▲" : "▼"} ${pct(v.drift_pct)} vs baseline`
          }
          accent={driftUp ? "up" : driftDown ? "down" : undefined}
        />
        <Tile label="Cargo cost" value={usdCompact(v.cargo_cost_usd)} sub={`bunker $${num(v.bunker_usd_t)}/t`} />
        <Tile
          label="Voyage progress"
          value={v.progress_pct == null ? "—" : `${v.progress_pct.toFixed(0)}%`}
          sub={
            v.distance_remaining_nm == null
              ? lv
                ? "resolving…"
                : "no vessel assigned"
              : `${num(v.distance_remaining_nm)} / ${num(v.distance_total_nm)} nm left`
          }
        />
        <Tile
          label="Routed ETA"
          value={v.eta_ts ? etaLabel(v.eta_ts).split(" · ")[1] : "—"}
          sub={v.eta_ts ? `${etaLabel(v.eta_ts).split(" · ")[0]} @ ${num(v.speed_used_kn, 1)} kn` : "assign a vessel"}
        />
      </div>

      {v.progress_pct != null && (
        <div className="h-1.5 w-full overflow-hidden rounded-pill bg-fog">
          <div className="h-full rounded-pill bg-graphite" style={{ width: `${v.progress_pct}%` }} />
        </div>
      )}

      <div className="card">
        <div className="mb-2 flex items-center justify-between">
          <span className="eyebrow">delivered cost/t — since baseline</span>
          <span className="meta">
            baseline {usd(s.baseline_usd_per_t, 2)}/t
            {s.baseline_at ? ` · ${new Date(s.baseline_at).toUTCString().slice(5, 16)}` : ""}
          </span>
        </div>
        <CostHistory d={d} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-tight">
          <span className="eyebrow">assigned vessel</span>
          {lv ? (
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-sans text-[13px]">
              <dt className="text-slate">Name</dt>
              <dd className="text-graphite">{lv.name ?? `MMSI ${lv.mmsi}`}</dd>
              <dt className="text-slate">MMSI</dt>
              <dd className="num text-graphite">{lv.mmsi}</dd>
              {lv.type && (
                <>
                  <dt className="text-slate">Type</dt>
                  <dd className="text-graphite">{lv.type}</dd>
                </>
              )}
              <dt className="text-slate">Position</dt>
              <dd className="num text-graphite">
                {lv.lat != null ? `${lv.lat.toFixed(2)}, ${lv.lon?.toFixed(2)}` : "—"}
              </dd>
              <dt className="text-slate">Speed</dt>
              <dd className="num text-graphite">
                {lv.sog_kn != null ? `${lv.sog_kn.toFixed(1)} kn` : "—"}
                {lv.cog_deg != null ? ` · ${Math.round(lv.cog_deg)}°` : ""}
              </dd>
              <dt className="text-slate">Status</dt>
              <dd className="text-graphite">{lv.nav_status ?? "—"}</dd>
              <dt className="text-slate">Last fix</dt>
              <dd className="text-graphite">
                {relAge(lv.ts)} · {lv.source === "estimated" ? "dead-reckoned" : "AIS"}
              </dd>
              {lv.destination && (
                <>
                  <dt className="text-slate">Dest (AIS)</dt>
                  <dd className="text-graphite">
                    {lv.destination}
                    {lv.eta_raw ? ` · ETA ${lv.eta_raw}` : ""}
                  </dd>
                </>
              )}
            </dl>
          ) : (
            <AssignVessel refId={refId} onDone={() => { load(); onChanged(); }} />
          )}
        </div>

        <div className="card-tight">
          <span className="eyebrow">why this class</span>
          <p className="caption mt-2 text-graphite">
            {d.analysis.recommendation?.why ?? "No feasible vessel class for this lane."}
          </p>
          {d.analysis.emissions && (
            <p className="meta mt-2">
              {d.analysis.emissions.recommended_kt} kt CO₂ · {d.analysis.emissions.recommended_g_per_t_nm} g/t·nm
              {" · greenest feasible: "}
              {d.analysis.emissions.greenest_feasible}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="field-label mr-1">set status</span>
        {STATUSES.map((st) => (
          <button
            key={st}
            type="button"
            className={`rounded-pill px-3 py-1 font-sans text-[12px] transition-colors ${
              s.status === st ? "bg-graphite text-canvas" : "bg-fog text-steel hover:text-graphite"
            }`}
            onClick={() => setStatus(st)}
            disabled={busy || s.status === st}
          >
            {st.replace("_", " ")}
          </button>
        ))}
      </div>
    </div>
  );
}

function AssignVessel({ refId, onDone }: { refId: string; onDone: () => void }) {
  const [mmsi, setMmsi] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="mt-2 space-y-2">
      <p className="meta">No vessel assigned — the cost still updates, but there is no live position or ETA.</p>
      <div className="flex gap-2">
        <input
          className="field num"
          placeholder="vessel MMSI"
          value={mmsi}
          onChange={(e) => setMmsi(e.target.value)}
        />
        <button
          type="button"
          className="btn !py-1.5"
          disabled={busy || !mmsi.trim()}
          onClick={async () => {
            setBusy(true);
            try {
              await api.patchShipment(refId, { assigned_mmsi: Number(mmsi.trim()) });
              onDone();
            } finally {
              setBusy(false);
            }
          }}
        >
          Assign
        </button>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
export function ShipmentsView({ vessels }: { vessels: VesselRef[] }) {
  const [list, setList] = useState<Shipment[]>([]);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [reason, setReason] = useState<string | undefined>();
  const [sel, setSel] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .shipments()
      .then((r) => {
        setEnabled(r.enabled);
        setReason(r.reason);
        setList(r.shipments);
        setSel((cur) => cur ?? r.shipments[0]?.ref ?? null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(load, [load]);

  const selected = useMemo(() => list.find((s) => s.ref === sel) ?? null, [list, sel]);

  if (enabled === false) {
    return (
      <div className="card-signature">
        <h2 className="h-section">Shipment tracking</h2>
        <p className="caption mt-3 max-w-2xl">
          This view needs a database. Set <code>DATABASE_URL</code> on the API (Supabase) and the
          worker, then reload. {reason ? <span className="text-slate">({reason})</span> : null}
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[360px_1fr]">
      <div className="space-y-3">
        <NewShipmentForm
          vessels={vessels}
          onCreated={(s) => {
            setList((cur) => [s, ...cur]);
            setSel(s.ref);
          }}
        />
        {err && <p className="caption text-ember">{err}</p>}
        {enabled === null && <p className="meta">loading…</p>}
        {list.map((s) => {
          const lc = s.latest_cost;
          const drift = lc?.drift_usd_per_t ?? null;
          return (
            <button
              key={s.ref}
              type="button"
              onClick={() => setSel(s.ref)}
              className={`block w-full rounded-md border p-3 text-left transition-colors ${
                s.ref === sel ? "border-graphite bg-fog" : "border-mist bg-canvas hover:border-slate"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-display text-[13px] text-graphite">{s.ref}</span>
                <span className={`rounded-pill px-2 py-0.5 font-sans text-[10px] ${STATUS_STYLE[s.status]}`}>
                  {s.status.replace("_", " ")}
                </span>
              </div>
              <div className="meta mt-1 truncate">
                {s.origin_code} → {s.dest_code} · {num(s.cargo_t)} t
              </div>
              <div className="mt-1.5 flex items-center justify-between font-sans text-[12px]">
                <span className="num text-graphite">
                  {lc ? `$${lc.delivered_usd_per_t.toFixed(2)}/t` : usd(s.baseline_usd_per_t, 2) + "/t"}
                </span>
                {drift != null && Math.abs(drift) >= 0.01 && (
                  <span className={drift > 0 ? "text-ember" : "text-[#2f6b31]"}>
                    {drift > 0 ? "▲" : "▼"} ${Math.abs(drift).toFixed(2)}
                  </span>
                )}
              </div>
              {lc?.progress_pct != null && (
                <div className="mt-1.5 h-1 w-full overflow-hidden rounded-pill bg-mist">
                  <div className="h-full bg-graphite" style={{ width: `${lc.progress_pct}%` }} />
                </div>
              )}
            </button>
          );
        })}
        {enabled && list.length === 0 && (
          <p className="meta">No shipments yet — track one to see live delivered cost and ETA.</p>
        )}
      </div>

      <div>
        {selected ? (
          <DetailPanel
            refId={selected.ref}
            onChanged={load}
            onDeleted={() => {
              setSel(null);
              load();
            }}
          />
        ) : (
          <div className="card">
            <p className="meta">Select a shipment, or track a new one.</p>
          </div>
        )}
      </div>
    </div>
  );
}

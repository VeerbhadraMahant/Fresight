import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { PortHit } from "../types";

/**
 * Search-as-you-type port selector backed by /api/reference/ports/search
 * (the ~200-port global registry). Emits the resolved port code.
 */
export function PortPicker({
  label,
  value,
  onChange,
  hint,
  placeholder = "search any port — name, code, country…",
}: {
  label: string;
  value: string;
  onChange: (code: string) => void;
  hint?: string;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<PortHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [display, setDisplay] = useState<string>(value);
  const boxRef = useRef<HTMLLabelElement>(null);

  // resolve the current code -> a human label (name · country)
  useEffect(() => {
    let live = true;
    if (!value) {
      setDisplay("");
      return;
    }
    api
      .resolvePort(value)
      .then((p) => live && setDisplay(`${p.name}${p.country ? ` · ${p.country}` : ""}`))
      .catch(() => live && setDisplay(value));
    return () => {
      live = false;
    };
  }, [value]);

  // debounced search while typing
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 2) {
      setHits([]);
      return;
    }
    setLoading(true);
    const t = setTimeout(() => {
      api
        .portSearch(q)
        .then((r) => setHits(r.results))
        .catch(() => setHits([]))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(t);
  }, [query, open]);

  // click-away closes the dropdown
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  function pick(p: PortHit) {
    onChange(p.code);
    setDisplay(`${p.name}${p.country ? ` · ${p.country}` : ""}`);
    setQuery("");
    setOpen(false);
  }

  return (
    <label ref={boxRef} className="relative block">
      <span className="field-label">{label}</span>
      <input
        className="field"
        value={open ? query : display}
        placeholder={placeholder}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => {
          setOpen(true);
          setQuery(e.target.value);
        }}
        autoComplete="off"
      />
      {hint && !open && <span className="meta mt-1 block">{hint}</span>}

      {open && (
        <div className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto border border-mist bg-canvas shadow-lg">
          {loading && <div className="meta px-3 py-2">searching…</div>}
          {!loading && query.trim().length >= 2 && hits.length === 0 && (
            <div className="meta px-3 py-2">no ports match “{query.trim()}”</div>
          )}
          {!loading && query.trim().length < 2 && (
            <div className="meta px-3 py-2">type at least 2 characters</div>
          )}
          {hits.map((p) => (
            <button
              key={p.code}
              type="button"
              className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left font-sans text-[13px] hover:bg-fog"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(p)}
            >
              <span className="text-graphite">
                {p.name}
                {p.country ? <span className="text-slate"> · {p.country}</span> : null}
              </span>
              <span className="meta shrink-0">
                {p.code} · {p.max_draft_m} m{p.curated ? " · calibrated" : ""}
              </span>
            </button>
          ))}
        </div>
      )}
    </label>
  );
}

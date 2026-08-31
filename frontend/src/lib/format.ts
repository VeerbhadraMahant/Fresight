export const usd = (n: number | null | undefined, digits = 0) =>
  n == null
    ? "—"
    : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: digits });

export const usdCompact = (n: number | null | undefined) => {
  if (n == null) return "—";
  const abs = Math.abs(n);
  const s = n < 0 ? "−" : "";
  if (abs >= 1e9) return `${s}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${s}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${s}$${(abs / 1e3).toFixed(0)}k`;
  return `${s}$${abs.toFixed(0)}`;
};

export const num = (n: number | null | undefined, digits = 0) =>
  n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: digits });

export const pct = (n: number | null | undefined, digits = 1) =>
  n == null ? "—" : `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toFixed(digits)}%`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const MONTH_NAMES = MONTHS;

export const shortDate = (iso: string) => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${MONTHS[d.getMonth()]} ’${String(d.getFullYear()).slice(2)}`;
};

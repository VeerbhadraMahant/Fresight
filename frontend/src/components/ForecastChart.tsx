import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Forecast } from "../types";
import { shortDate } from "../lib/format";
import { C } from "../lib/theme";

export function ForecastChart({ fc }: { fc: Forecast }) {
  const rows: Record<string, unknown>[] = [];
  fc.history.forEach((h) => rows.push({ date: h.date, hist: h.rate }));
  const last = fc.history[fc.history.length - 1];
  if (last) rows.push({ date: last.date, mean: last.rate, band: [last.rate, last.rate] });
  fc.forecast.forEach((f) => rows.push({ date: f.date, mean: f.mean, band: [f.lo, f.hi] }));

  const all = [
    ...fc.history.map((h) => h.rate),
    ...fc.forecast.map((f) => f.hi),
    ...fc.forecast.map((f) => f.lo),
  ];
  const yMin = Math.floor(Math.min(...all) * 0.92);
  const yMax = Math.ceil(Math.max(...all) * 1.06);

  return (
    <div>
      <div className="mb-3 flex items-center gap-5">
        <LegendKey color={C.graphite} label="Actual" />
        <LegendKey color={C.ember} label="Forecast (ensemble)" dashed />
        <span className="meta">band = 80% interval</span>
      </div>
      <div className="h-[300px] w-full">
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <XAxis
              dataKey="date"
              tickFormatter={shortDate}
              minTickGap={44}
              tickLine={false}
              axisLine={{ stroke: C.mist }}
              tick={{ fill: C.slate }}
              dy={6}
            />
            <YAxis
              domain={[yMin, yMax]}
              width={46}
              tickLine={false}
              axisLine={false}
              tick={{ fill: C.slate }}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip
              cursor={{ stroke: C.slate, strokeDasharray: "3 3" }}
              labelFormatter={(l) => shortDate(String(l))}
              formatter={(v: unknown, name: string) => {
                if (name === "band" && Array.isArray(v)) return [`$${v[0]} – $${v[1]}/t`, "80% interval"];
                return [`$${Number(v).toFixed(1)}/t`, name === "hist" ? "actual" : "forecast"];
              }}
            />
            <ReferenceLine x={last?.date} stroke={C.brass} strokeDasharray="4 3" />
            <Area
              type="monotone"
              dataKey="band"
              stroke="none"
              fill={C.ivory}
              fillOpacity={1}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="hist"
              stroke={C.graphite}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="mean"
              stroke={C.ember}
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function LegendKey({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 font-sans text-[12px] text-steel">
      <span
        className="inline-block h-0 w-5 align-middle"
        style={{ borderTop: `2px ${dashed ? "dashed" : "solid"} ${color}` }}
      />
      {label}
    </span>
  );
}

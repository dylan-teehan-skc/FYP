"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TimelinePoint } from "@/lib/types";

interface SavingsChartProps {
  points: TimelinePoint[];
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  label?: string;
  payload?: TooltipPayloadItem[];
}

function CustomTooltip({ active, label, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs shadow-lg">
      <p className="mb-1.5 font-medium text-zinc-300">{label}</p>
      {payload.map((item) => (
        <div key={item.name} className="flex items-center gap-2">
          <div
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-zinc-400">{item.name}:</span>
          <span className="font-mono tabular-nums text-zinc-200">
            {(item.value * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export function SavingsChart({ points }: SavingsChartProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-muted-foreground">No timeline data available</p>
      </div>
    );
  }

  const formatted = points.map((p) => ({
    date: new Date(p.date).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
    }),
    guided_pct: p.guided_pct,
    success_rate: p.success_rate,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart
        data={formatted}
        margin={{ top: 4, right: 8, left: -8, bottom: 0 }}
      >
        <defs>
          <linearGradient id="gradGuided" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#34d399" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradSuccess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickMargin={8}
        />
        <YAxis
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          domain={[0, 1]}
          tickMargin={4}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: "#71717a", paddingTop: 8 }}
          formatter={(value: string) =>
            value === "guided_pct" ? "Guided %" : "Success Rate"
          }
        />
        <Area
          type="monotone"
          dataKey="guided_pct"
          stroke="#34d399"
          strokeWidth={2}
          fill="url(#gradGuided)"
          dot={false}
          activeDot={{ r: 4, fill: "#34d399", strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="success_rate"
          stroke="#60a5fa"
          strokeWidth={2}
          fill="url(#gradSuccess)"
          dot={false}
          activeDot={{ r: 4, fill: "#60a5fa", strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

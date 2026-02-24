"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from "recharts";
import type { BottleneckTool } from "@/lib/types";
import { formatDuration, formatCost } from "@/lib/format";

interface BottleneckChartProps {
  tools: BottleneckTool[];
}

interface ScatterPoint {
  x: number;
  y: number;
  z: number;
  name: string;
  cost: number;
  isHot: boolean;
}

interface CustomDotProps {
  cx?: number;
  cy?: number;
  payload?: ScatterPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: ScatterPoint }>;
}

function CustomDot({ cx = 0, cy = 0, payload }: CustomDotProps) {
  if (!payload) return <g />;
  const color = payload.isHot ? "#f87171" : "#fbbf24";
  return (
    <circle
      cx={cx}
      cy={cy}
      r={Math.max(4, Math.min(18, Math.sqrt(payload.z) * 0.4))}
      fill={color}
      fillOpacity={0.75}
      stroke={color}
      strokeWidth={1}
      strokeOpacity={0.9}
    />
  );
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs shadow-lg">
      <p className="mb-1.5 font-medium text-zinc-100">{d.name}</p>
      <div className="space-y-0.5">
        <div className="flex gap-2">
          <span className="text-zinc-400">Calls:</span>
          <span className="font-mono tabular-nums text-zinc-200">{d.x.toLocaleString()}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-zinc-400">Avg latency:</span>
          <span className="font-mono tabular-nums text-zinc-200">{formatDuration(d.y)}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-zinc-400">Total cost:</span>
          <span className="font-mono tabular-nums text-zinc-200">{formatCost(d.cost)}</span>
        </div>
      </div>
    </div>
  );
}

export function BottleneckChart({ tools }: BottleneckChartProps) {
  if (tools.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-muted-foreground">No bottleneck data available</p>
      </div>
    );
  }

  const medianCalls = [...tools].sort((a, b) => a.call_count - b.call_count)[
    Math.floor(tools.length / 2)
  ].call_count;
  const medianDuration = [...tools].sort(
    (a, b) => a.avg_duration_ms - b.avg_duration_ms
  )[Math.floor(tools.length / 2)].avg_duration_ms;

  const data: ScatterPoint[] = tools.map((t) => ({
    x: t.call_count,
    y: t.avg_duration_ms,
    z: t.total_cost_usd * 10000, // scale for ZAxis / dot size
    name: t.tool_name,
    cost: t.total_cost_usd,
    isHot: t.call_count >= medianCalls && t.avg_duration_ms >= medianDuration,
  }));

  return (
    <div className="relative">
      <div className="mb-3 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-red-400 opacity-75" />
          <span>High freq + high latency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-amber-400 opacity-75" />
          <span>Other tools</span>
        </div>
        <span className="ml-auto">Dot size = total cost</span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 8, right: 24, left: -8, bottom: 8 }}>
          <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="x"
            name="Call Count"
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            label={{
              value: "Call frequency",
              position: "insideBottomRight",
              offset: -4,
              fill: "#52525b",
              fontSize: 10,
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Avg Duration"
            tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}s`}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            label={{
              value: "Avg latency",
              angle: -90,
              position: "insideLeft",
              offset: 12,
              fill: "#52525b",
              fontSize: 10,
            }}
          />
          <ZAxis type="number" dataKey="z" range={[40, 800]} />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={data}
            shape={(props: object) => <CustomDot {...(props as CustomDotProps)} />}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

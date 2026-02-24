"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ClusterWorkflow } from "@/lib/types";
import { formatDuration } from "@/lib/format";

interface ClusterPerformanceChartProps {
  workflows: ClusterWorkflow[];
}

interface ChartPoint {
  x: number;
  y: number;
  workflow_id: string;
  task_description: string | null;
  mode: string;
  status: string;
  duration_ms: number | null;
  timestamp: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  const description = d.task_description ?? "(no description)";
  const truncated =
    description.length > 60 ? description.slice(0, 60) + "…" : description;
  const statusColor =
    d.status === "success"
      ? "#34d399"
      : d.status === "failure"
        ? "#f87171"
        : "#fbbf24";
  return (
    <div className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs shadow-lg">
      <p className="mb-1.5 max-w-[220px] font-medium text-zinc-100">
        {truncated}
      </p>
      <div className="space-y-0.5">
        <div className="flex gap-2">
          <span className="text-zinc-400">Mode:</span>
          <span
            className="font-medium tabular-nums"
            style={{
              color: d.mode === "guided" ? "#34d399" : "#60a5fa",
            }}
          >
            {d.mode === "guided" ? "Guided" : "Exploration"}
          </span>
        </div>
        <div className="flex gap-2">
          <span className="text-zinc-400">Duration:</span>
          <span className="font-mono tabular-nums text-zinc-200">
            {formatDuration(d.duration_ms)}
          </span>
        </div>
        <div className="flex gap-2">
          <span className="text-zinc-400">Status:</span>
          <span className="font-medium tabular-nums" style={{ color: statusColor }}>
            {d.status}
          </span>
        </div>
      </div>
    </div>
  );
}

export function ClusterPerformanceChart({
  workflows,
}: ClusterPerformanceChartProps) {
  if (workflows.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center">
        <p className="text-sm text-muted-foreground">No workflow data available</p>
      </div>
    );
  }

  const sortedWorkflows = [...workflows].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  const explorationData: ChartPoint[] = sortedWorkflows
    .filter((w) => w.mode === "exploration")
    .map((w) => ({
      x: new Date(w.timestamp).getTime(),
      y: (w.duration_ms ?? 0) / 1000,
      ...w,
    }));

  const guidedData: ChartPoint[] = sortedWorkflows
    .filter((w) => w.mode === "guided")
    .map((w) => ({
      x: new Date(w.timestamp).getTime(),
      y: (w.duration_ms ?? 0) / 1000,
      ...w,
    }));

  const xTickFormatter = (value: number) =>
    new Date(value).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
    });

  const yTickFormatter = (value: number) => `${value.toFixed(0)}s`;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
        <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="x"
          domain={["auto", "auto"]}
          tickFormatter={xTickFormatter}
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickMargin={8}
        />
        <YAxis
          type="number"
          dataKey="y"
          tickFormatter={yTickFormatter}
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickMargin={4}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: "#71717a", paddingTop: 8 }}
          formatter={(value: string) =>
            value === "exploration" ? "Exploration" : "Guided"
          }
        />
        <Scatter
          name="exploration"
          data={explorationData}
          fill="#60a5fa"
          fillOpacity={0.8}
          r={5}
        />
        <Scatter
          name="guided"
          data={guidedData}
          fill="#34d399"
          fillOpacity={0.8}
          r={5}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

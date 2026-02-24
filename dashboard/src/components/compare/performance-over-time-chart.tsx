"use client";

import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { WorkflowListItem } from "@/lib/types";
import { formatDuration } from "@/lib/format";

interface PerformanceOverTimeChartProps {
  workflows: WorkflowListItem[];
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

interface TrendPoint {
  x: number;
  y: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}

function rollingAverage(
  points: { x: number; y: number }[],
  window = 3
): TrendPoint[] {
  return points.map((p, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = points.slice(start, i + 1);
    return {
      x: p.x,
      y: slice.reduce((s, v) => s + v.y, 0) / slice.length,
    };
  });
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  if (!d.workflow_id) return null;
  const description = d.task_description ?? "(no description)";
  const truncated =
    description.length > 60 ? description.slice(0, 60) + "\u2026" : description;
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
          <span
            className="font-medium tabular-nums"
            style={{ color: statusColor }}
          >
            {d.status}
          </span>
        </div>
      </div>
    </div>
  );
}

export function PerformanceOverTimeChart({
  workflows,
}: PerformanceOverTimeChartProps) {
  if (workflows.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center">
        <p className="text-sm text-muted-foreground">
          No workflow data available
        </p>
      </div>
    );
  }

  const sortedWorkflows = [...workflows].sort(
    (a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const explorationData: ChartPoint[] = sortedWorkflows
    .filter((w) => w.mode === "exploration")
    .map((w) => ({
      x: new Date(w.timestamp).getTime(),
      y: (w.duration_ms ?? 0) / 1000,
      workflow_id: w.workflow_id,
      task_description: w.task_description,
      mode: w.mode,
      status: w.status,
      duration_ms: w.duration_ms,
      timestamp: w.timestamp,
    }));

  const guidedData: ChartPoint[] = sortedWorkflows
    .filter((w) => w.mode === "guided")
    .map((w) => ({
      x: new Date(w.timestamp).getTime(),
      y: (w.duration_ms ?? 0) / 1000,
      workflow_id: w.workflow_id,
      task_description: w.task_description,
      mode: w.mode,
      status: w.status,
      duration_ms: w.duration_ms,
      timestamp: w.timestamp,
    }));

  const explorationTrend = rollingAverage(explorationData, 3);
  const guidedTrend = rollingAverage(guidedData, 3);

  const allTimestamps = sortedWorkflows.map((w) =>
    new Date(w.timestamp).getTime()
  );
  const xMin = Math.min(...allTimestamps);
  const xMax = Math.max(...allTimestamps);

  const allYValues = [
    ...explorationData.map((d) => d.y),
    ...guidedData.map((d) => d.y),
  ];
  const yMax = allYValues.length > 0 ? Math.ceil(Math.max(...allYValues) * 1.15) : 10;

  const explorationMean =
    explorationData.length > 0
      ? explorationData.reduce((s, d) => s + d.y, 0) / explorationData.length
      : null;
  const guidedMean =
    guidedData.length > 0
      ? guidedData.reduce((s, d) => s + d.y, 0) / guidedData.length
      : null;

  const transitionX =
    guidedData.length > 0 ? guidedData[0].x : null;

  const xTickFormatter = (value: number) =>
    new Date(value).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
    });

  const yTickFormatter = (value: number) => `${value.toFixed(0)}s`;

  return (
    <div className="h-[420px]">
      {/* Guided sub-chart (top) */}
      <div className="relative h-[200px]">
        <div className="absolute right-5 top-0 z-10 flex items-center gap-1.5 rounded-bl-md bg-card/80 px-2 py-1">
          <div className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-[11px] font-medium text-emerald-400">Guided</span>
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
            <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[xMin, xMax]}
              tickFormatter={xTickFormatter}
              tick={false}
              axisLine={false}
              tickLine={false}
              height={1}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, yMax]}
              tickFormatter={yTickFormatter}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickMargin={4}
            />
            {guidedMean !== null && (
              <ReferenceLine
                y={guidedMean}
                stroke="#34d399"
                strokeDasharray="3 6"
                strokeOpacity={0.5}
                label={{
                  value: `Avg: ${guidedMean.toFixed(1)}s`,
                  position: "left",
                  fill: "#34d399",
                  fontSize: 10,
                }}
              />
            )}
            {transitionX !== null && (
              <ReferenceLine
                x={transitionX}
                stroke="#71717a"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: "Guided starts",
                  position: "insideTopLeft",
                  fill: "#a1a1aa",
                  fontSize: 10,
                }}
              />
            )}
            <Tooltip content={<CustomTooltip />} />
            <Scatter
              name="Guided"
              data={guidedData}
              fill="#34d399"
              fillOpacity={0.8}
              r={5}
            />
            {guidedTrend.length >= 2 && (
              <Line
                data={guidedTrend}
                dataKey="y"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Guided trend"
                legendType="none"
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Divider line */}
      <div className="mx-4 border-t border-border/60" />

      {/* Exploration sub-chart (bottom) */}
      <div className="relative h-[200px]">
        <div className="absolute right-5 top-0 z-10 flex items-center gap-1.5 rounded-bl-md bg-card/80 px-2 py-1">
          <div className="h-2 w-2 rounded-full bg-blue-400" />
          <span className="text-[11px] font-medium text-blue-400">Exploration</span>
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
            <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[xMin, xMax]}
              tickFormatter={xTickFormatter}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickMargin={8}
              allowDuplicatedCategory={false}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, yMax]}
              tickFormatter={yTickFormatter}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickMargin={4}
            />
            {explorationMean !== null && (
              <ReferenceLine
                y={explorationMean}
                stroke="#60a5fa"
                strokeDasharray="3 6"
                strokeOpacity={0.5}
                label={{
                  value: `Avg: ${explorationMean.toFixed(1)}s`,
                  position: "left",
                  fill: "#60a5fa",
                  fontSize: 10,
                }}
              />
            )}
            {transitionX !== null && (
              <ReferenceLine
                x={transitionX}
                stroke="#71717a"
                strokeDasharray="4 4"
                strokeWidth={1.5}
              />
            )}
            <Tooltip content={<CustomTooltip />} />
            <Scatter
              name="Exploration"
              data={explorationData}
              fill="#60a5fa"
              fillOpacity={0.8}
              r={5}
            />
            {explorationTrend.length >= 2 && (
              <Line
                data={explorationTrend}
                dataKey="y"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Exploration trend"
                legendType="none"
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

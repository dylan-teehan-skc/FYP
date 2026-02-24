"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import type { EventOut } from "@/lib/types";
import { formatDuration } from "@/lib/format";

interface TraceTimelineProps {
  events: EventOut[];
}

interface TimelineBar {
  name: string;
  start: number;
  duration: number;
  status: string;
  toolName: string;
  stepNumber: number;
}

function statusColor(status: string): string {
  if (status === "success") return "#34d399"; // emerald-400
  if (status === "failure") return "#f87171"; // red-400
  return "#fbbf24"; // amber-400
}

interface TooltipPayload {
  payload: TimelineBar;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded border border-border bg-zinc-900 px-3 py-2 text-xs shadow-none">
      <p className="font-medium text-foreground mb-1">
        {d.stepNumber}. {d.toolName}
      </p>
      <p className="text-muted-foreground">
        Start:{" "}
        <span className="font-mono tabular-nums text-foreground">
          {formatDuration(d.start)}
        </span>
      </p>
      <p className="text-muted-foreground">
        Duration:{" "}
        <span className="font-mono tabular-nums text-foreground">
          {formatDuration(d.duration)}
        </span>
      </p>
      <p className="text-muted-foreground">
        Status:{" "}
        <span
          style={{ color: statusColor(d.status) }}
          className="font-medium"
        >
          {d.status}
        </span>
      </p>
    </div>
  );
}

export function TraceTimeline({ events }: TraceTimelineProps) {
  const toolEvents = events.filter((e) => e.tool_name !== null);

  if (toolEvents.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        No tool calls to display in timeline.
      </div>
    );
  }

  // Build cumulative start times from sorted step_number order
  const sorted = [...toolEvents].sort((a, b) => a.step_number - b.step_number);

  let cursor = 0;
  const bars: TimelineBar[] = sorted.map((event) => {
    const bar: TimelineBar = {
      name: `${event.step_number}`,
      start: cursor,
      duration: Math.max(event.duration_ms, 50), // min 50ms for visibility
      status: event.status,
      toolName: event.tool_name as string,
      stepNumber: event.step_number,
    };
    cursor += Math.max(event.duration_ms, 50);
    return bar;
  });

  // Recharts stacked bar trick: render two bars per row — invisible "start" bar + colored "duration" bar
  const chartData = bars.map((b) => ({
    ...b,
    // "gap" is the transparent offset bar
    gap: b.start,
  }));

  const totalDuration = cursor;
  const barHeight = 36;
  const chartHeight = Math.max(bars.length * (barHeight + 8) + 40, 120);

  // Tick formatter for X axis
  function formatTick(value: number): string {
    if (value === 0) return "0";
    if (value < 1000) return `${Math.round(value)}ms`;
    return `${(value / 1000).toFixed(1)}s`;
  }

  // Generate readable X axis ticks
  const tickCount = Math.min(6, Math.max(3, Math.ceil(totalDuration / 1000)));
  const tickValues: number[] = [];
  for (let i = 0; i <= tickCount; i++) {
    tickValues.push(Math.round((totalDuration / tickCount) * i));
  }

  return (
    <div className="w-full" style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 24, left: 8 }}
          barSize={barHeight}
          barGap={0}
        >
          <XAxis
            type="number"
            domain={[0, totalDuration]}
            ticks={tickValues}
            tickFormatter={formatTick}
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={{ stroke: "#3f3f46" }}
            tickLine={{ stroke: "#3f3f46" }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={28}
            tick={{ fontSize: 10, fill: "#71717a", fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          {/* Invisible offset bar */}
          <Bar dataKey="gap" stackId="a" fill="transparent" isAnimationActive={false} />
          {/* Visible duration bar */}
          <Bar
            dataKey="duration"
            stackId="a"
            radius={[2, 2, 2, 2]}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="toolName"
              position="insideLeft"
              style={{
                fontSize: 11,
                fill: "rgba(255,255,255,0.85)",
                fontFamily: "var(--font-mono)",
              }}
            />
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={statusColor(entry.status)}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

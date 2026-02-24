"use client";

import { memo } from "react";
import {
  Handle,
  Position,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { formatDuration } from "@/lib/format";

export interface ToolNodeData extends Record<string, unknown> {
  label: string;
  call_count: number;
  avg_duration_ms: number;
  isOptimal?: boolean;
}

export type ToolNodeType = Node<ToolNodeData, "tool">;

function getLatencyColor(ms: number): {
  border: string;
  dot: string;
  label: string;
} {
  if (ms < 500) {
    return {
      border: "border-emerald-500/60",
      dot: "bg-emerald-500",
      label: "text-emerald-400",
    };
  }
  if (ms < 2000) {
    return {
      border: "border-amber-500/60",
      dot: "bg-amber-500",
      label: "text-amber-400",
    };
  }
  return {
    border: "border-red-500/60",
    dot: "bg-red-500",
    label: "text-red-400",
  };
}

export const ToolNode = memo(function ToolNode({
  data,
  selected,
}: NodeProps<ToolNodeType>) {
  const { label, call_count, avg_duration_ms, isOptimal } = data;
  const colors = getLatencyColor(avg_duration_ms);

  return (
    <div
      className={[
        "relative flex w-44 flex-col gap-1.5 rounded-md border px-3 py-2.5",
        "bg-zinc-800 text-white transition-all",
        selected
          ? "border-blue-400 ring-1 ring-blue-400/40"
          : colors.border,
        isOptimal ? "ring-1 ring-emerald-500/50" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-zinc-600 !bg-zinc-500"
      />

      <div className="flex items-center gap-1.5">
        <span
          className={`mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full ${colors.dot}`}
        />
        <span className="truncate text-xs font-semibold leading-tight text-white">
          {label}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tabular-nums text-zinc-400">
          {call_count.toLocaleString()}x
        </span>
        <span className={`font-mono text-[10px] tabular-nums ${colors.label}`}>
          {formatDuration(avg_duration_ms)}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-zinc-600 !bg-zinc-500"
      />
    </div>
  );
});

"use client";

import { X, Clock, Hash, Zap } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
import type { ToolNodeData } from "./tool-node";

interface DetailPanelProps {
  node: ToolNodeData | null;
  onClose: () => void;
}

function LatencyBadge({ ms }: { ms: number }) {
  if (ms < 500) {
    return (
      <span className="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[10px] font-medium tabular-nums text-emerald-400 ring-1 ring-emerald-500/30">
        Fast
      </span>
    );
  }
  if (ms < 2000) {
    return (
      <span className="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[10px] font-medium tabular-nums text-amber-400 ring-1 ring-amber-500/30">
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[10px] font-medium tabular-nums text-red-400 ring-1 ring-red-500/30">
      Slow
    </span>
  );
}

export function DetailPanel({ node, onClose }: DetailPanelProps) {
  if (!node) return null;

  return (
    <div className="absolute right-3 top-3 z-10 w-64">
      <Card className="border-zinc-700 bg-zinc-800 shadow-none">
        <CardHeader className="pb-0">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-sm font-semibold text-white leading-tight">
              {node.label}
            </CardTitle>
            <button
              onClick={onClose}
              className="mt-0.5 flex-shrink-0 rounded p-0.5 text-zinc-400 transition-colors hover:bg-zinc-700 hover:text-white"
              aria-label="Close panel"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="mt-1">
            <LatencyBadge ms={node.avg_duration_ms} />
          </div>
        </CardHeader>

        <CardContent className="pt-3">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-400">
                <Hash className="h-3.5 w-3.5" />
                <span className="text-xs">Call count</span>
              </div>
              <span className="font-mono text-xs font-semibold tabular-nums text-white">
                {node.call_count.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-400">
                <Clock className="h-3.5 w-3.5" />
                <span className="text-xs">Avg duration</span>
              </div>
              <span
                className={[
                  "font-mono text-xs font-semibold tabular-nums",
                  node.avg_duration_ms < 500
                    ? "text-emerald-400"
                    : node.avg_duration_ms < 2000
                      ? "text-amber-400"
                      : "text-red-400",
                ].join(" ")}
              >
                {formatDuration(node.avg_duration_ms)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-400">
                <Zap className="h-3.5 w-3.5" />
                <span className="text-xs">Optimal path</span>
              </div>
              <span
                className={[
                  "font-mono text-xs font-semibold tabular-nums",
                  node.isOptimal ? "text-emerald-400" : "text-zinc-500",
                ].join(" ")}
              >
                {node.isOptimal ? "Yes" : "No"}
              </span>
            </div>
          </div>

          <div className="mt-3 border-t border-zinc-700 pt-3">
            <p className="text-[10px] text-zinc-500">
              Click a node in the graph to inspect its execution statistics.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

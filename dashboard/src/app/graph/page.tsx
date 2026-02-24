"use client";

import { ExecutionDag } from "@/components/graph/execution-dag";
import { InfoTooltip } from "@/components/ui/info-tooltip";

export default function GraphPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-shrink-0 border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Execution Graph{" "}
              <InfoTooltip text="Directed acyclic graph of tool-to-tool transitions observed across all workflow executions. Each node is a tool, each edge is a transition between consecutive tool calls. Thicker edges = more frequent transitions." />
            </h1>
            <p className="text-sm text-muted-foreground">
              Tool transition DAG — node color indicates latency, edge thickness
              indicates frequency. Animated edges follow optimal paths.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>Fast (&lt;500ms)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <span>Medium (&lt;2s)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              <span>Slow (&gt;2s)</span>
            </div>
            <div className="ml-2 flex items-center gap-1.5 border-l border-zinc-700 pl-4">
              <svg width="20" height="4" aria-hidden="true">
                <line
                  x1="0"
                  y1="2"
                  x2="20"
                  y2="2"
                  stroke="#10b981"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />
              </svg>
              <span>Optimal path</span>
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <ExecutionDag />
      </div>
    </div>
  );
}

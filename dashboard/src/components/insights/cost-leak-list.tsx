"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDuration, formatCost } from "@/lib/format";
import type { BottleneckTool } from "@/lib/types";

interface CostLeakListProps {
  tools: BottleneckTool[];
}

function RedundancyBadge() {
  return (
    <Badge
      variant="outline"
      className="border-amber-500/30 bg-amber-500/10 text-amber-400"
    >
      redundant
    </Badge>
  );
}

export function CostLeakList({ tools }: CostLeakListProps) {
  if (tools.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No tool data available
      </p>
    );
  }

  const sorted = [...tools].sort((a, b) => b.total_cost_usd - a.total_cost_usd);
  const maxCost = sorted[0]?.total_cost_usd ?? 1;

  return (
    <div className="space-y-2">
      {sorted.map((tool, idx) => {
        const isRedundant = tool.avg_calls_per_workflow > 2;
        const barPct = maxCost > 0 ? (tool.total_cost_usd / maxCost) * 100 : 0;

        return (
          <Card key={tool.tool_name} className="border-border bg-card">
            <CardContent className="p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  #{idx + 1}
                </span>
                <span className="flex-1 truncate text-sm font-medium text-foreground">
                  {tool.tool_name}
                </span>
                {isRedundant && <RedundancyBadge />}
              </div>

              {/* horizontal cost bar */}
              <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full rounded-full transition-all ${
                    isRedundant ? "bg-amber-400" : "bg-blue-400"
                  }`}
                  style={{ width: `${barPct}%` }}
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Total cost
                  </p>
                  <p className="font-mono text-sm tabular-nums text-foreground">
                    {formatCost(tool.total_cost_usd)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Avg latency
                  </p>
                  <p className="font-mono text-sm tabular-nums text-foreground">
                    {formatDuration(tool.avg_duration_ms)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Calls / workflow
                  </p>
                  <p
                    className={`font-mono text-sm tabular-nums ${
                      isRedundant ? "text-amber-400" : "text-foreground"
                    }`}
                  >
                    {tool.avg_calls_per_workflow.toFixed(1)}×
                  </p>
                </div>
              </div>

              {isRedundant && (
                <p className="mt-2 text-xs text-amber-400/80">
                  Called {tool.avg_calls_per_workflow.toFixed(1)}× per workflow on
                  average — potential redundant invocations
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

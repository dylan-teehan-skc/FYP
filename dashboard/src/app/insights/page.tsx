"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { BottleneckChart } from "@/components/insights/bottleneck-chart";
import { CostLeakList } from "@/components/insights/cost-leak-list";
import { api } from "@/lib/api";
import type { BottlenecksResponse, BottleneckTool } from "@/lib/types";
import { formatCost, formatDuration } from "@/lib/format";
import { InfoTooltip } from "@/components/ui/info-tooltip";

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
      {children}
    </p>
  );
}

function SummaryPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border border-border bg-muted/30 px-3 py-2">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={`font-mono text-base font-semibold tabular-nums ${accent ?? "text-foreground"}`}
      >
        {value}
      </span>
    </div>
  );
}

export default function InsightsPage() {
  const [data, setData] = useState<BottlenecksResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getBottlenecks()
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load data");
      });
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  const tools = data?.tools ?? [];

  // Aggregate summary stats
  const totalCost = tools.reduce((sum, t) => sum + t.total_cost_usd, 0);
  const redundantCount = tools.filter((t) => t.avg_calls_per_workflow > 2).length;
  const slowestTool = tools.reduce<BottleneckTool | null>(
    (best, t) => (!best || t.avg_duration_ms > best.avg_duration_ms ? t : best),
    null
  );
  const mostCalled = tools.reduce<BottleneckTool | null>(
    (best, t) => (!best || t.call_count > best.call_count ? t : best),
    null
  );

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          Optimization Insights{" "}
          <InfoTooltip text="Tool-level analysis identifying cost leaks, latency bottlenecks, and redundant calls across all workflow executions. Use this to find which tools are expensive, slow, or called more often than necessary." />
        </h1>
        <p className="text-sm text-muted-foreground">
          Tool-level cost, latency, and redundancy analysis
        </p>
      </div>

      {/* Summary strip */}
      {!data ? (
        <div className="mb-6 grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : (
        <div className="mb-6 grid grid-cols-4 gap-3">
          <SummaryPill label="Tools tracked" value={String(tools.length)} />
          <SummaryPill
            label="Total cost"
            value={formatCost(totalCost)}
            accent="text-foreground"
          />
          <SummaryPill
            label="Redundant tools"
            value={String(redundantCount)}
            accent={redundantCount > 0 ? "text-amber-400" : "text-foreground"}
          />
          <SummaryPill
            label="Slowest tool"
            value={
              slowestTool
                ? `${slowestTool.tool_name} (${formatDuration(slowestTool.avg_duration_ms)})`
                : "-"
            }
            accent="text-red-400"
          />
        </div>
      )}

      {/* Scatter plot */}
      <Card className="mb-6 border-border bg-card">
        <CardContent className="p-5">
          <SectionLabel>
            Bottleneck map — frequency vs latency (dot size = total cost)
          </SectionLabel>
          {!data ? (
            <div className="h-72 animate-pulse rounded bg-muted" />
          ) : (
            <BottleneckChart tools={tools} />
          )}
        </CardContent>
      </Card>

      {/* Cost leak list */}
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Cost Leaks</h2>
          <p className="text-xs text-muted-foreground">
            Ranked by total cost — amber highlights redundant callers
          </p>
        </div>
        {mostCalled && (
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            Most called: {mostCalled.tool_name} ({mostCalled.call_count.toLocaleString()}×)
          </span>
        )}
      </div>

      {!data ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : (
        <CostLeakList tools={tools} />
      )}
    </div>
  );
}

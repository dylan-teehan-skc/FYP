"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, Hash, Activity, DollarSign } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TraceTimeline } from "@/components/traces/trace-timeline";
import { StepTable } from "@/components/traces/step-table";
import { Conformance } from "@/components/traces/conformance";
import { OptimizationContext } from "@/components/traces/optimization-context";
import { api } from "@/lib/api";
import {
  formatDuration,
  formatTimestamp,
  formatCost,
  formatNumber,
} from "@/lib/format";
import type { TraceOut, OptimalPath, ComparisonResponse } from "@/lib/types";

function MetaChip({
  icon: Icon,
  label,
  value,
  tooltip,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  tooltip?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      {tooltip && <InfoTooltip text={tooltip} />}
      <span className="font-mono tabular-nums text-foreground">{value}</span>
    </div>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  const isGuided = mode === "guided";
  return (
    <Badge
      variant="outline"
      className={
        isGuided
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
          : "border-blue-500/30 bg-blue-500/10 text-blue-400"
      }
    >
      {isGuided ? "Guided" : "Exploration"}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "success"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
      : status === "failure"
        ? "border-red-500/30 bg-red-500/10 text-red-400"
        : "border-amber-500/30 bg-amber-500/10 text-amber-400";
  return (
    <Badge variant="outline" className={cls}>
      {status}
    </Badge>
  );
}

function SectionHeader({ title, tooltip }: { title: string; tooltip?: string }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">
      {title}
      {tooltip && (
        <>
          {" "}
          <InfoTooltip text={tooltip} />
        </>
      )}
    </p>
  );
}

function SkeletonBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-8 animate-pulse rounded bg-muted" />
      ))}
    </div>
  );
}

export default function TraceDetailPage() {
  const params = useParams<{ id: string }>();
  const workflowId = params.id;

  const [trace, setTrace] = useState<TraceOut | null>(null);
  const [optimalPaths, setOptimalPaths] = useState<OptimalPath[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workflowId) return;

    Promise.all([
      api.getWorkflowTrace(workflowId),
      api.getOptimalPaths(),
      api.getComparison().catch(() => null),
    ])
      .then(([traceData, pathsData, compData]) => {
        setTrace(traceData);
        setOptimalPaths(pathsData.paths);
        setComparison(compData);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load trace");
      })
      .finally(() => setLoading(false));
  }, [workflowId]);

  // Derive summary stats from events — all safe because `trace` is checked before rendering
  const events = trace?.events ?? [];
  const firstEvent = events[0] ?? null;
  const lastEvent = events.length > 1 ? events[events.length - 1] : null;

  const totalDurationMs = events.reduce((sum, e) => sum + e.duration_ms, 0);

  const totalCost = events.reduce((sum, e) => sum + (e.cost_usd ?? 0), 0);

  const totalTokens = events.reduce(
    (sum, e) => sum + e.llm_prompt_tokens + e.llm_completion_tokens,
    0,
  );

  const overallStatus = events.some((e) => e.status === "failure")
    ? "failure"
    : events.some((e) => e.status === "timeout")
      ? "timeout"
      : "success";

  const mode =
    firstEvent?.agent_role.toLowerCase().includes("guided")
      ? "guided"
      : "exploration";

  return (
    <div className="p-6">
      {/* Back nav */}
      <div className="mb-4">
        <Link
          href="/traces"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Traces
        </Link>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="h-6 w-80 animate-pulse rounded bg-muted" />
          <SkeletonBlock rows={3} />
          <SkeletonBlock rows={6} />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-6">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      ) : trace ? (
        <div className="space-y-4">
          {/* Page header */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                Trace Detail
              </h1>
              <p className="mt-0.5 font-mono text-xs text-muted-foreground tabular-nums">
                {workflowId}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={overallStatus} />
              <ModeBadge mode={mode} />
            </div>
          </div>

          {/* Metadata strip */}
          <Card className="border-border bg-card py-4 shadow-none">
            <CardContent className="px-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <MetaChip
                  icon={Hash}
                  label="Steps"
                  value={formatNumber(trace.total_events)}
                  tooltip="Total number of tool calls made in this workflow execution."
                />
                <MetaChip
                  icon={Clock}
                  label="Duration"
                  value={formatDuration(totalDurationMs)}
                  tooltip="Total wall-clock time of all tool calls summed."
                />
                <MetaChip
                  icon={Activity}
                  label="Tokens"
                  value={formatNumber(totalTokens)}
                  tooltip="Total LLM tokens consumed (prompt + completion) across all reasoning steps."
                />
                <MetaChip
                  icon={DollarSign}
                  label="Cost"
                  value={formatCost(totalCost)}
                  tooltip="Estimated cost of LLM API calls for this workflow."
                />
                {firstEvent && (
                  <div className="ml-auto text-xs text-muted-foreground">
                    {formatTimestamp(firstEvent.timestamp)}
                    {lastEvent && lastEvent !== firstEvent && (
                      <> &rarr; {formatTimestamp(lastEvent.timestamp)}</>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-2">
              <SectionHeader title="Timeline" tooltip="Gantt chart of every tool call in this workflow. Bar width shows duration, colour shows status. Hover for details." />
              <TraceTimeline events={trace.events} />
            </CardContent>
          </Card>

          {/* Conformance */}
          <Conformance events={trace.events} optimalPaths={optimalPaths} />

          {/* Optimization Context */}
          <OptimizationContext
            events={trace.events}
            optimalPaths={optimalPaths}
            mode={mode}
            totalDurationMs={totalDurationMs}
            totalSteps={trace.total_events}
            totalCost={totalCost}
            overallStatus={overallStatus}
            comparison={comparison}
          />

          {/* Step breakdown */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-2">
              <SectionHeader title="Step Breakdown" tooltip="Detailed table of each tool call in execution order — tool name, input/output, duration, cost, and status." />
              <StepTable events={trace.events} />
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

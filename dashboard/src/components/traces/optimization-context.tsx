"use client";

import { Card, CardContent } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { findBestMatch } from "@/lib/path-matching";
import { formatDuration, formatDelta, formatNumber } from "@/lib/format";
import type { EventOut, OptimalPath, ComparisonResponse } from "@/lib/types";

interface OptimizationContextProps {
  events: EventOut[];
  optimalPaths: OptimalPath[];
  mode: "guided" | "exploration";
  totalDurationMs: number;
  totalSteps: number;
  totalCost: number;
  overallStatus: string;
  comparison: ComparisonResponse | null;
}

function MetricComparison({
  label,
  actual,
  baseline,
  format,
  lowerIsBetter,
  baselineLabel,
}: {
  label: string;
  actual: number;
  baseline: number;
  format: (v: number) => string;
  lowerIsBetter: boolean;
  baselineLabel: string;
}) {
  const { label: deltaLabel, pct, improved: rawImproved } = formatDelta(baseline, actual);
  const isGood = lowerIsBetter ? rawImproved : !rawImproved;
  const accentClass =
    pct === 0
      ? "text-muted-foreground"
      : isGood
        ? "text-emerald-400"
        : "text-red-400";
  const badgeBg =
    pct === 0
      ? "bg-muted text-muted-foreground"
      : isGood
        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
        : "bg-red-500/15 text-red-400 border border-red-500/25";

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={`font-mono text-base font-semibold tabular-nums ${accentClass}`}>
        {format(actual)}
      </span>
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground/60">
          {baselineLabel}: {format(baseline)}
        </span>
        {pct !== 0 && (
          <span
            className={`inline-flex rounded-full px-1.5 py-0 font-mono text-[10px] font-medium tabular-nums ${badgeBg}`}
          >
            {deltaLabel}
          </span>
        )}
      </div>
    </div>
  );
}

export function OptimizationContext({
  events,
  optimalPaths,
  mode,
  totalDurationMs,
  totalSteps,
  overallStatus,
  comparison,
}: OptimizationContextProps) {
  const toolEvents = events.filter((e) => e.tool_name !== null);
  const toolSequence = toolEvents.map((e) => e.tool_name as string);
  const match = findBestMatch(toolSequence, optimalPaths);

  if (toolSequence.length === 0) return null;

  const isGuided = mode === "guided";
  const dotClass = isGuided ? "bg-emerald-400" : "bg-blue-400";
  const modeLabel = isGuided ? "Guided Mode" : "Exploration Mode";
  const modeTextClass = isGuided ? "text-emerald-400" : "text-blue-400";

  // No matching path — show minimal context
  if (!match) {
    return (
      <Card className="border-border bg-card shadow-none">
        <CardContent className="px-4 pt-4 pb-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Optimization Context
              </p>
              <InfoTooltip text="Shows how the optimization system affected this workflow — which optimal path was matched, and how performance compares to the baseline." />
            </div>
          </div>
          <div className="flex items-center gap-2 mb-3">
            <div className={`h-2 w-2 rounded-full ${dotClass}`} />
            <span className={`text-sm font-semibold ${modeTextClass}`}>
              {modeLabel}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            No matching optimal path found for this workflow type.
            The system needs at least 30 successful executions of similar tasks
            to establish an optimal path.
          </p>
        </CardContent>
      </Card>
    );
  }

  const bestPath = match.path;
  const conformancePct = Math.round(match.score * 100);
  const actualSuccess = overallStatus === "success" ? 1 : 0;

  // Exploration baseline from comparison endpoint
  const expStats = comparison?.exploration;
  const hasExpBaseline = expStats != null && expStats.count > 0;
  const hasGuidedData = (comparison?.guided?.count ?? 0) > 0;

  return (
    <Card className="border-border bg-card shadow-none">
      <CardContent className="px-4 pt-4 pb-4">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Optimization Context
            </p>
            <InfoTooltip text="Shows how the optimization system affected this workflow — which optimal path was matched, and how performance compares to the baseline." />
          </div>
        </div>

        {/* Mode + Match info */}
        <div className={`flex items-center gap-3 ${hasGuidedData ? "mb-4" : ""}`}>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${dotClass}`} />
            <span className={`text-sm font-semibold ${modeTextClass}`}>
              {modeLabel}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            Matched: &ldquo;{bestPath.task_cluster}&rdquo;
          </span>
          <span className="font-mono text-xs tabular-nums text-muted-foreground/60">
            {conformancePct}% conformance
          </span>
        </div>

        {!hasGuidedData ? (
          <p className="mt-3 text-sm text-muted-foreground">
            Run workflows in guided mode to see optimization comparisons.
          </p>
        ) : (
          <>
            {/* Performance vs Optimal Baseline */}
            <div className="mb-4">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                {isGuided ? "Performance vs Optimal Baseline" : "What Optimization Could Save"}
              </p>
              <div className="grid grid-cols-3 gap-4">
                <MetricComparison
                  label="Duration"
                  actual={totalDurationMs}
                  baseline={bestPath.avg_duration_ms}
                  format={formatDuration}
                  lowerIsBetter={true}
                  baselineLabel="optimal"
                />
                <MetricComparison
                  label="Steps"
                  actual={totalSteps}
                  baseline={bestPath.avg_steps}
                  format={formatNumber}
                  lowerIsBetter={true}
                  baselineLabel="optimal"
                />
                <MetricComparison
                  label="Success Rate"
                  actual={actualSuccess * 100}
                  baseline={bestPath.success_rate * 100}
                  format={(v) => `${v.toFixed(0)}%`}
                  lowerIsBetter={false}
                  baselineLabel="optimal"
                />
              </div>
            </div>

            {/* Savings vs Exploration Average (only if data exists) */}
            {hasExpBaseline && (
              <div className="border-t border-border pt-4">
                <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                  {isGuided ? "Savings vs Exploration Average" : "Exploration Baseline"}
                </p>
                <div className="grid grid-cols-3 gap-4">
                  <MetricComparison
                    label="Duration"
                    actual={totalDurationMs}
                    baseline={expStats.avg_duration_ms}
                    format={formatDuration}
                    lowerIsBetter={true}
                    baselineLabel="explore avg"
                  />
                  <MetricComparison
                    label="Steps"
                    actual={totalSteps}
                    baseline={expStats.avg_steps}
                    format={formatNumber}
                    lowerIsBetter={true}
                    baselineLabel="explore avg"
                  />
                  <MetricComparison
                    label="Success Rate"
                    actual={actualSuccess * 100}
                    baseline={(expStats.success_rate ?? 0) * 100}
                    format={(v) => `${v.toFixed(0)}%`}
                    lowerIsBetter={false}
                    baselineLabel="explore avg"
                  />
                </div>
              </div>
            )}

            {/* Optimal path metadata */}
            <div className="mt-4 flex items-center gap-4 border-t border-border pt-3 text-[10px] text-muted-foreground/50 tabular-nums font-mono">
              <span>Optimal path: {bestPath.execution_count} executions</span>
              <span>{(bestPath.success_rate * 100).toFixed(0)}% success rate</span>
              <span>{bestPath.tool_sequence.length} steps</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

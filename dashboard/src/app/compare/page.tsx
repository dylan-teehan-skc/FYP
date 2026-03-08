"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { DeltaCard } from "@/components/compare/delta-card";
import { SavingsChart } from "@/components/compare/savings-chart";
import { PerformanceOverTimeChart } from "@/components/compare/performance-over-time-chart";
import { api } from "@/lib/api";
import { formatDuration, formatPercent, formatNumber, formatCost } from "@/lib/format";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import type { ComparisonResponse, TimelineResponse, WorkflowListResponse } from "@/lib/types";

function SectionLabel({ children, tooltip }: { children: ReactNode; tooltip?: string }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
      {children}
      {tooltip && (
        <>
          {" "}
          <InfoTooltip text={tooltip} />
        </>
      )}
    </p>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-2.5 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-mono text-sm font-medium tabular-nums text-foreground">
        {value}
      </span>
    </div>
  );
}

function ModeColumn({
  title,
  accentClass,
  dotClass,
  stats,
}: {
  title: string;
  accentClass: string;
  dotClass: string;
  stats: { label: string; value: string }[];
}) {
  return (
    <Card className="border-border bg-card">
      <CardContent className="p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${dotClass}`} />
          <span className={`text-sm font-semibold ${accentClass}`}>{title}</span>
        </div>
        <div>
          {stats.map((s) => (
            <StatRow key={s.label} label={s.label} value={s.value} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SkeletonCard() {
  return (
    <Card className="border-border bg-card">
      <CardContent className="p-5">
        <div className="h-24 animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}

export default function ComparePage() {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [allWorkflows, setAllWorkflows] = useState<WorkflowListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getComparison(),
      api.getTimeline(),
      api.getWorkflows(500, 0),
    ])
      .then(([comp, tl, wfs]) => {
        setComparison(comp);
        setTimeline(tl);
        setAllWorkflows(wfs);
      })
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

  const exp = comparison?.exploration;
  const guided = comparison?.guided;

  // Duration: ms → seconds for readability (null-safe)
  const expDurS = exp?.avg_duration_ms != null
    ? parseFloat((exp.avg_duration_ms / 1000).toFixed(1)) : 0;
  const guidedDurS = guided?.avg_duration_ms != null
    ? parseFloat((guided.avg_duration_ms / 1000).toFixed(1)) : 0;

  const expSteps = exp?.avg_steps != null
    ? parseFloat(exp.avg_steps.toFixed(1)) : 0;
  const guidedSteps = guided?.avg_steps != null
    ? parseFloat(guided.avg_steps.toFixed(1)) : 0;

  const expSucc = exp?.success_rate != null
    ? parseFloat((exp.success_rate * 100).toFixed(1)) : 0;
  const guidedSucc = guided?.success_rate != null
    ? parseFloat((guided.success_rate * 100).toFixed(1)) : 0;

  // Cost in cents for DeltaCard
  const expCost = exp?.avg_cost_usd != null
    ? parseFloat((exp.avg_cost_usd * 100).toFixed(2)) : 0;
  const guidedCost = guided?.avg_cost_usd != null
    ? parseFloat((guided.avg_cost_usd * 100).toFixed(2)) : 0;

  const guidedHasData = (guided?.count ?? 0) > 0;

  const explorationStats = exp
    ? [
        { label: "Avg Duration", value: formatDuration(exp.avg_duration_ms) },
        { label: "Avg Steps", value: formatNumber(exp.avg_steps) },
        { label: "Success Rate", value: formatPercent(exp.success_rate) },
        { label: "Avg Cost", value: formatCost(exp.avg_cost_usd ?? null) },
        { label: "Workflows", value: formatNumber(exp.count) },
      ]
    : [];

  const guidedStats = guided
    ? guidedHasData
      ? [
          {
            label: "Avg Duration",
            value: formatDuration(guided.avg_duration_ms),
          },
          { label: "Avg Steps", value: formatNumber(guided.avg_steps) },
          { label: "Success Rate", value: formatPercent(guided.success_rate) },
          { label: "Avg Cost", value: formatCost(guided.avg_cost_usd ?? null) },
          { label: "Workflows", value: formatNumber(guided.count) },
        ]
      : [
          { label: "Avg Duration", value: "-" },
          { label: "Avg Steps", value: "-" },
          { label: "Success Rate", value: "-" },
          { label: "Avg Cost", value: "-" },
          { label: "Workflows", value: "0" },
        ]
    : [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          Path Comparison{" "}
          <InfoTooltip text="Head-to-head comparison of exploration mode (agent discovers paths freely) vs guided mode (agent follows historically optimal paths). Lower duration and steps with higher success rate indicates guided mode is working." />
        </h1>
        <p className="text-sm text-muted-foreground">
          Exploration baseline vs guided optimized mode — head-to-head metrics
        </p>
      </div>

      {comparison && exp?.count === 0 && guided?.count === 0 && (
        <Card className="mb-6 border-amber-500/20 bg-amber-500/5">
          <CardContent className="p-4">
            <p className="text-sm text-amber-400">
              No mode data available yet. Run workflows with guided mode enabled
              to see exploration vs guided comparisons. The demo agent needs to
              emit optimize:guided / optimize:exploration events.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Delta cards */}
      <div className="mb-6 grid grid-cols-3 gap-3 xl:grid-cols-5">
        {!comparison ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <DeltaCard
              label="Avg Duration"
              before={expDurS}
              after={guidedDurS}
              unit="s"
              lowerIsBetter={true}
              hasData={guidedHasData}
            />
            <DeltaCard
              label="Avg Steps"
              before={expSteps}
              after={guidedSteps}
              unit="steps"
              lowerIsBetter={true}
              hasData={guidedHasData}
            />
            <DeltaCard
              label="Success Rate"
              before={expSucc}
              after={guidedSucc}
              unit="%"
              lowerIsBetter={false}
              hasData={guidedHasData}
            />
            <DeltaCard
              label="Avg Cost"
              before={expCost}
              after={guidedCost}
              unit="¢"
              lowerIsBetter={true}
              hasData={guidedHasData}
            />
            <DeltaCard
              label="API Calls"
              before={expSteps}
              after={guidedSteps}
              unit="calls"
              lowerIsBetter={true}
              hasData={guidedHasData}
            />
          </>
        )}
      </div>

      {/* Dual-column mode breakdown */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        {!comparison ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <ModeColumn
              title="Exploration"
              accentClass="text-blue-400"
              dotClass="bg-blue-400"
              stats={explorationStats}
            />
            <ModeColumn
              title="Guided"
              accentClass="text-emerald-400"
              dotClass="bg-emerald-400"
              stats={guidedStats}
            />
          </>
        )}
      </div>

      {/* Performance over time scatter chart */}
      <Card className="mb-6 border-border bg-card">
        <CardContent className="p-5">
          <SectionLabel tooltip="Each dot is one workflow run. Exploration (blue) and guided (green) are separated vertically for clarity. Both charts share the same Y-axis scale. Trend lines show rolling averages.">Performance over time</SectionLabel>
          {!allWorkflows ? (
            <div className="h-[420px] animate-pulse rounded bg-muted" />
          ) : (
            <PerformanceOverTimeChart workflows={allWorkflows.workflows} />
          )}
        </CardContent>
      </Card>

      {/* Savings over time */}
      <Card className="border-border bg-card">
        <CardContent className="p-5">
          <SectionLabel tooltip="Tracks how guided mode adoption and success rate change over time. Rising guided ratio with stable or improving success rate confirms the optimization system is effective.">Guided adoption and success rate over time</SectionLabel>
          {!timeline ? (
            <div className="h-64 animate-pulse rounded bg-muted" />
          ) : (
            <SavingsChart points={timeline.points} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

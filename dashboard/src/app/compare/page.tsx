"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { DeltaCard } from "@/components/compare/delta-card";
import { SavingsChart } from "@/components/compare/savings-chart";
import { api } from "@/lib/api";
import { formatDuration, formatPercent, formatNumber, formatCost } from "@/lib/format";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import type { ComparisonResponse, TimelineResponse, SavingsResponse } from "@/lib/types";

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
      {children}
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
  const [savings, setSavings] = useState<SavingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getComparison(),
      api.getTimeline(),
      api.getSavings().catch(() => null),
    ])
      .then(([comp, tl, sav]) => {
        setComparison(comp);
        setTimeline(tl);
        setSavings(sav);
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

  const explorationStats = exp
    ? [
        { label: "Avg Duration", value: formatDuration(exp.avg_duration_ms) },
        { label: "Avg Steps", value: formatNumber(exp.avg_steps) },
        { label: "Success Rate", value: formatPercent(exp.success_rate) },
        { label: "Workflows", value: formatNumber(exp.count) },
      ]
    : [];

  const guidedStats = guided
    ? [
        {
          label: "Avg Duration",
          value: formatDuration(guided.avg_duration_ms),
        },
        { label: "Avg Steps", value: formatNumber(guided.avg_steps) },
        { label: "Success Rate", value: formatPercent(guided.success_rate) },
        { label: "Workflows", value: formatNumber(guided.count) },
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
            />
            <DeltaCard
              label="Avg Steps"
              before={expSteps}
              after={guidedSteps}
              unit="steps"
              lowerIsBetter={true}
            />
            <DeltaCard
              label="Success Rate"
              before={expSucc}
              after={guidedSucc}
              unit="%"
              lowerIsBetter={false}
            />
            <Card className="border-border bg-card">
              <CardContent className="p-5">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Cost Saved
                </p>
                <span className="font-mono text-2xl font-semibold tabular-nums text-emerald-400">
                  {savings ? formatCost(savings.cost_saved_usd) : "-"}
                </span>
                {savings && savings.pct_duration_improvement > 0 && (
                  <div className="mt-3">
                    <span className="inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2.5 py-0.5 font-mono text-sm font-semibold tabular-nums text-emerald-400">
                      ↓{savings.pct_duration_improvement.toFixed(0)}% faster
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card className="border-border bg-card">
              <CardContent className="p-5">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  API Calls Reduced
                </p>
                <span className="font-mono text-2xl font-semibold tabular-nums text-emerald-400">
                  {expSteps > guidedSteps
                    ? `−${(expSteps - guidedSteps).toFixed(1)}`
                    : formatNumber(expSteps - guidedSteps)}
                </span>
                <span className="ml-1.5 text-sm text-muted-foreground">
                  per workflow
                </span>
                {savings && savings.pct_steps_improvement > 0 && (
                  <div className="mt-3">
                    <span className="inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2.5 py-0.5 font-mono text-sm font-semibold tabular-nums text-emerald-400">
                      ↓{savings.pct_steps_improvement.toFixed(0)}% fewer calls
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
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

      {/* Savings over time */}
      <Card className="border-border bg-card">
        <CardContent className="p-5">
          <SectionLabel>Guided adoption and success rate over time</SectionLabel>
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

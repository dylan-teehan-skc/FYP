"use client";

import { useEffect, useState } from "react";
import { Activity, Clock, CheckCircle, Layers } from "lucide-react";
import { StatCard } from "@/components/dashboard/stat-card";
import { SavingsBanner } from "@/components/dashboard/savings-banner";
import { ModeDonut } from "@/components/dashboard/mode-donut";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { api } from "@/lib/api";
import { formatDuration, formatPercent, formatNumber } from "@/lib/format";
import type { AnalyticsSummary } from "@/lib/types";

export default function OverviewPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    api.getAnalyticsSummary().then(setSummary).catch(console.error);
  }, []);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          Overview{" "}
          <InfoTooltip text="High-level summary of all workflow executions captured by the SDK. Metrics update as agents run more tasks." />
        </h1>
        <p className="text-sm text-muted-foreground">
          Workflow optimization metrics and recent activity
        </p>
      </div>

      <div className="mb-6 grid grid-cols-4 gap-3">
        <StatCard
          label="Total Workflows"
          value={summary ? formatNumber(summary.total_workflows) : "-"}
          icon={Activity}
          subtitle={`${summary ? formatNumber(summary.total_events) : "-"} events`}
          accentColor="text-foreground"
          tooltip="Total number of end-to-end agent workflow executions captured by the SDK."
        />
        <StatCard
          label="Avg Duration"
          value={summary ? formatDuration(summary.avg_duration_ms) : "-"}
          icon={Clock}
          accentColor="text-foreground"
          tooltip="Mean wall-clock time from workflow start to completion, across all runs."
        />
        <StatCard
          label="Success Rate"
          value={summary ? formatPercent(summary.success_rate) : "-"}
          icon={CheckCircle}
          accentColor={
            summary && summary.success_rate && summary.success_rate >= 0.85
              ? "text-emerald-400"
              : "text-amber-400"
          }
          tooltip="Proportion of workflows that completed their task successfully. Green when above 85%."
        />
        <StatCard
          label="Avg Steps"
          value={summary ? formatNumber(summary.avg_steps) : "-"}
          icon={Layers}
          tooltip="Average number of tool calls per workflow. Guided mode typically reduces this."
        />
      </div>

      <div className="mb-6">
        <SavingsBanner />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <ActivityFeed />
        </div>
        <ModeDonut />
      </div>
    </div>
  );
}

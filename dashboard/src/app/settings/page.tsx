"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { AnalyticsSummary } from "@/lib/types";
import { Database, Activity, Server } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";

const THRESHOLDS = [
  {
    label: "Similarity Threshold",
    value: "0.85",
    description: "Minimum cosine similarity for semantic path matching",
  },
  {
    label: "Min Executions",
    value: "30",
    description: "Minimum workflow executions before guided mode activates",
  },
  {
    label: "Min Success Rate",
    value: "0.85",
    description: "Minimum historical success rate to trust an optimal path",
  },
  {
    label: "NED Threshold",
    value: "0.55",
    description:
      "Normalized edit distance cutoff for trace sub-clustering (HAC)",
  },
  {
    label: "Bottleneck Threshold",
    value: "40%",
    description: "Duration percentage to flag a tool as a bottleneck",
  },
];

function HealthIndicator({
  label,
  icon: Icon,
  status,
}: {
  label: string;
  icon: typeof Database;
  status: "online" | "offline" | "checking";
}) {
  const color =
    status === "online"
      ? "bg-emerald-400"
      : status === "offline"
        ? "bg-red-400"
        : "bg-amber-400 animate-pulse";
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm">{label}</span>
      <div className="ml-auto flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${color}`} />
        <span className="text-xs text-muted-foreground capitalize">
          {status}
        </span>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [collectorStatus, setCollectorStatus] = useState<
    "online" | "offline" | "checking"
  >("checking");

  useEffect(() => {
    api
      .getAnalyticsSummary()
      .then((data) => {
        setSummary(data);
        setCollectorStatus("online");
      })
      .catch(() => setCollectorStatus("offline"));
  }, []);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          Settings{" "}
          <InfoTooltip text="System configuration thresholds that control when guided mode activates, how optimal paths are selected, and how bottlenecks are detected. Health checks confirm backend services are reachable." />
        </h1>
        <p className="text-sm text-muted-foreground">
          System configuration and health monitoring
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Analysis Thresholds
            </p>
            <div className="space-y-3">
              {THRESHOLDS.map((t) => (
                <div
                  key={t.label}
                  className="flex items-start justify-between border-b border-border/50 pb-3 last:border-0 last:pb-0"
                >
                  <div>
                    <p className="text-sm">{t.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {t.description}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className="ml-4 shrink-0 font-mono tabular-nums"
                  >
                    {t.value}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <Card className="border-border bg-card">
            <CardContent className="p-4">
              <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                System Health
              </p>
              <div className="space-y-3">
                <HealthIndicator
                  label="Collector API"
                  icon={Server}
                  status={collectorStatus}
                />
                <HealthIndicator
                  label="PostgreSQL + pgvector"
                  icon={Database}
                  status={collectorStatus}
                />
                <HealthIndicator
                  label="Analysis Engine"
                  icon={Activity}
                  status={collectorStatus}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardContent className="p-4">
              <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Data Summary
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">Workflows</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.total_workflows) : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Events</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.total_events) : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Top Tools</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.top_tools.length) : "-"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

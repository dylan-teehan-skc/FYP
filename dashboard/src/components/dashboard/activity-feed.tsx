"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatDuration, formatTimestamp } from "@/lib/format";
import type { WorkflowListItem } from "@/lib/types";

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

function StatusDot({ status }: { status: string }) {
  const color =
    status === "success"
      ? "bg-emerald-400"
      : status === "failure"
        ? "bg-red-400"
        : "bg-amber-400";
  return <div className={`h-1.5 w-1.5 rounded-full ${color}`} />;
}

export function ActivityFeed() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getWorkflows(10, 0)
      .then((res) => setWorkflows(res.workflows))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="p-4">
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Recent Activity
        </p>
        <div className="space-y-0">
          {workflows.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No workflows recorded yet
            </p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2 text-xs font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="pb-2 text-xs font-medium text-muted-foreground">
                    Task
                  </th>
                  <th className="pb-2 text-xs font-medium text-muted-foreground">
                    Mode
                  </th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">
                    Duration
                  </th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">
                    Steps
                  </th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody>
                {workflows.map((wf) => (
                  <tr
                    key={wf.workflow_id}
                    className="border-b border-border/50 last:border-0"
                  >
                    <td className="py-2">
                      <StatusDot status={wf.status} />
                    </td>
                    <td className="max-w-[200px] truncate py-2 text-sm text-foreground">
                      {wf.task_description}
                    </td>
                    <td className="py-2">
                      <ModeBadge mode={wf.mode} />
                    </td>
                    <td className="py-2 text-right font-mono text-sm tabular-nums text-muted-foreground">
                      {formatDuration(wf.duration_ms)}
                    </td>
                    <td className="py-2 text-right font-mono text-sm tabular-nums text-muted-foreground">
                      {wf.steps}
                    </td>
                    <td className="py-2 text-right text-xs text-muted-foreground">
                      {formatTimestamp(wf.timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

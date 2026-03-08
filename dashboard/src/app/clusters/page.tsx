"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Boxes, ChevronDown, ChevronRight, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { formatDuration, formatPercent, formatTimestamp } from "@/lib/format";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ClusterGroup, ClusterWorkflow, TaskClusterSummary } from "@/lib/types";

function SuccessRateBadge({ rate }: { rate: number | null }) {
  if (rate === null || rate === undefined) {
    return <span className="text-sm text-muted-foreground">-</span>;
  }
  const colorClass =
    rate >= 0.85
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
      : rate >= 0.5
        ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
        : "border-red-500/30 bg-red-500/10 text-red-400";
  return (
    <Badge variant="outline" className={colorClass}>
      {formatPercent(rate)}
    </Badge>
  );
}

function aggregateSuccessRate(subs: TaskClusterSummary[]): number | null {
  const withRate = subs.filter((s) => s.success_rate !== null);
  if (withRate.length === 0) return null;
  const totalWf = withRate.reduce((a, s) => a + s.execution_count, 0);
  if (totalWf === 0) return null;
  return (
    withRate.reduce(
      (a, s) => a + (s.success_rate ?? 0) * s.execution_count,
      0,
    ) / totalWf
  );
}

function aggregateAvgDuration(subs: TaskClusterSummary[]): number | null {
  const withDur = subs.filter((s) => s.avg_duration_ms !== null);
  if (withDur.length === 0) return null;
  const totalWf = withDur.reduce((a, s) => a + s.execution_count, 0);
  if (totalWf === 0) return null;
  return (
    withDur.reduce(
      (a, s) => a + (s.avg_duration_ms ?? 0) * s.execution_count,
      0,
    ) / totalWf
  );
}

function SubClusterLabel({
  label,
}: {
  label: string;
  taskDescription?: string | null;
}) {
  const match = label.match(/\(subcluster_(\d+)\)$/);
  const variantNum = match ? parseInt(match[1]) + 1 : null;
  return (
    <span className="text-sm text-foreground">
      {variantNum ? `Variant ${variantNum}` : label}
    </span>
  );
}

const PAGE_SIZE = 5;
const WF_PAGE_SIZE = 5;

function StatusDot({ status }: { status: string }) {
  const colorClass =
    status === "success"
      ? "bg-emerald-400"
      : status === "failure"
        ? "bg-red-400"
        : "bg-amber-400";
  const labelClass =
    status === "success"
      ? "text-emerald-400"
      : status === "failure"
        ? "text-red-400"
        : "text-amber-400";
  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-1.5 w-1.5 rounded-full ${colorClass}`} />
      <span className={`text-xs font-medium capitalize ${labelClass}`}>
        {status}
      </span>
    </div>
  );
}

function WorkflowRunsSection({
  pathId,
  groupName,
}: {
  pathId?: string;
  groupName?: string;
}) {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<ClusterWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);
  const [page, setPage] = useState(0);

  useEffect(() => {
    if (pathId) {
      api
        .getClusterDetail(pathId)
        .then((d) => setWorkflows(d.workflows))
        .catch(() => {})
        .finally(() => setLoading(false));
    } else if (groupName) {
      api
        .getClusterGroupDetail(groupName)
        .then((d) => setWorkflows(d.workflows))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [pathId, groupName]);

  const totalPages = Math.max(1, Math.ceil(workflows.length / WF_PAGE_SIZE));
  const pagedWf = workflows.slice(
    page * WF_PAGE_SIZE,
    (page + 1) * WF_PAGE_SIZE,
  );

  return (
    <div className="border-t border-border">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        className="flex w-full items-center gap-2 px-5 py-2.5 text-xs font-medium uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        Workflow Runs{!loading && ` (${workflows.length})`}
      </button>

      {expanded && (
        <>
          {loading ? (
            <div className="px-5 pb-3">
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-6 animate-pulse rounded bg-muted"
                  />
                ))}
              </div>
            </div>
          ) : workflows.length === 0 ? (
            <div className="px-5 pb-4">
              <p className="text-xs text-muted-foreground">
                No workflow runs yet.
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="px-5 py-2 text-xs font-medium text-muted-foreground">
                      Status
                    </TableHead>
                    <TableHead className="px-4 py-2 text-xs font-medium text-muted-foreground">
                      Task
                    </TableHead>
                    <TableHead className="px-4 py-2 text-xs font-medium text-muted-foreground">
                      Mode
                    </TableHead>
                    <TableHead className="px-4 py-2 text-xs font-medium text-muted-foreground">
                      Duration
                    </TableHead>
                    <TableHead className="px-4 py-2 text-xs font-medium text-muted-foreground">
                      Steps
                    </TableHead>
                    <TableHead className="px-4 py-2 text-xs font-medium text-muted-foreground">
                      Timestamp
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedWf.map((wf) => (
                    <TableRow
                      key={wf.workflow_id}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/agents/${wf.workflow_id}`);
                      }}
                      className="border-border cursor-pointer transition-colors hover:bg-accent/30"
                    >
                      <TableCell className="px-5 py-2.5">
                        <StatusDot status={wf.status} />
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <span
                          className="block max-w-xs truncate text-sm text-foreground"
                          title={wf.task_description ?? undefined}
                        >
                          {wf.task_description ?? (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <Badge
                          variant="outline"
                          className={
                            wf.mode === "guided"
                              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                              : "border-blue-500/30 bg-blue-500/10 text-blue-400"
                          }
                        >
                          {wf.mode === "guided" ? "Guided" : "Exploration"}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <span className="font-mono tabular-nums text-sm text-muted-foreground">
                          {formatDuration(wf.duration_ms)}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <span className="font-mono tabular-nums text-sm text-muted-foreground">
                          {wf.steps ?? "—"}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <span className="tabular-nums text-xs text-muted-foreground">
                          {formatTimestamp(wf.timestamp)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-border px-5 py-2.5">
                  <span className="text-xs text-muted-foreground">
                    {page * WF_PAGE_SIZE + 1}&ndash;
                    {Math.min((page + 1) * WF_PAGE_SIZE, workflows.length)} of{" "}
                    {workflows.length} workflows
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPage((p) => Math.max(0, p - 1));
                      }}
                      disabled={page === 0}
                      className="rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                    >
                      Prev
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPage((p) => Math.min(totalPages - 1, p + 1));
                      }}
                      disabled={page >= totalPages - 1}
                      className="rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function GroupSection({ group }: { group: ClusterGroup }) {
  const router = useRouter();
  const isSingle = group.subclusters.length === 1;
  const [expanded, setExpanded] = useState(true);
  const [page, setPage] = useState(0);

  const aggSuccess = aggregateSuccessRate(group.subclusters);
  const aggDuration = aggregateAvgDuration(group.subclusters);

  const totalPages = Math.ceil(group.subclusters.length / PAGE_SIZE);
  const pagedSubs = group.subclusters.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE,
  );

  const groupHref = `/clusters/group/${encodeURIComponent(group.name)}`;

  if (isSingle) {
    const sub = group.subclusters[0];
    return (
      <Card className="border-border bg-card shadow-none">
        <div className="flex w-full items-center gap-4 px-5 py-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          <div
            onClick={() => router.push(groupHref)}
            className="min-w-0 flex-1 cursor-pointer"
          >
            <p className="truncate text-sm font-medium text-foreground transition-colors hover:text-blue-400">
              {group.name}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-6 text-sm">
            <span className="font-mono tabular-nums text-muted-foreground">
              {group.total_workflows} workflows
            </span>
            <SuccessRateBadge rate={sub.success_rate} />
            <span className="font-mono tabular-nums text-muted-foreground">
              {formatDuration(sub.avg_duration_ms)}
            </span>
            <span className="font-mono tabular-nums text-muted-foreground">
              {sub.tool_sequence.length} steps
            </span>
            <span className="tabular-nums text-xs text-muted-foreground">
              {formatTimestamp(sub.updated_at)}
            </span>
          </div>
        </div>
        {expanded && <WorkflowRunsSection groupName={group.name} />}
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card shadow-none">
      <div className="flex w-full items-center gap-4 px-5 py-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <div
          onClick={() => router.push(groupHref)}
          className="min-w-0 flex-1 cursor-pointer"
        >
          <p className="truncate text-sm font-medium text-foreground transition-colors hover:text-blue-400">
            {group.name}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-6 text-sm">
          <span className="font-mono tabular-nums text-muted-foreground">
            {group.total_workflows} workflows
          </span>
          <SuccessRateBadge rate={aggSuccess} />
          <span className="font-mono tabular-nums text-muted-foreground">
            {formatDuration(aggDuration)}
          </span>
          <Badge variant="outline" className="border-zinc-600/30 text-zinc-400">
            {group.subclusters.length} variants
          </Badge>
        </div>
      </div>

      {expanded && (
        <CardContent className="border-t border-border p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="px-5 py-2.5 text-xs font-medium text-muted-foreground">
                  Variant
                </TableHead>
                <TableHead className="px-4 py-2.5 text-xs font-medium text-muted-foreground">
                  Workflows
                </TableHead>
                <TableHead className="px-4 py-2.5 text-xs font-medium text-muted-foreground">
                  Success Rate
                </TableHead>
                <TableHead className="px-4 py-2.5 text-xs font-medium text-muted-foreground">
                  Avg Duration
                </TableHead>
                <TableHead className="px-4 py-2.5 text-xs font-medium text-muted-foreground">
                  Optimal Steps
                </TableHead>
                <TableHead className="px-4 py-2.5 text-xs font-medium text-muted-foreground">
                  Updated
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pagedSubs.map((sub) => (
                <TableRow
                  key={sub.path_id}
                  onClick={() => router.push(`/clusters/${sub.path_id}`)}
                  className="border-border cursor-pointer transition-colors hover:bg-accent/30"
                >
                  <TableCell className="px-5 py-3">
                    <SubClusterLabel
                      label={sub.task_cluster}
                      taskDescription={sub.task_description}
                    />
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <span className="font-mono tabular-nums text-sm text-muted-foreground">
                      {sub.workflow_count}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <SuccessRateBadge rate={sub.success_rate} />
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <span className="font-mono tabular-nums text-sm text-muted-foreground">
                      {formatDuration(sub.avg_duration_ms)}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <span className="font-mono tabular-nums text-sm text-muted-foreground">
                      {sub.tool_sequence.length}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <span className="tabular-nums text-xs text-muted-foreground">
                      {formatTimestamp(sub.updated_at)}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-5 py-2.5">
              <span className="text-xs text-muted-foreground">
                {page * PAGE_SIZE + 1}&ndash;
                {Math.min((page + 1) * PAGE_SIZE, group.subclusters.length)} of{" "}
                {group.subclusters.length} variants
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setPage((p) => Math.max(0, p - 1));
                  }}
                  disabled={page === 0}
                  className="rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setPage((p) => Math.min(totalPages - 1, p + 1));
                  }}
                  disabled={page >= totalPages - 1}
                  className="rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
          <WorkflowRunsSection groupName={group.name} />
        </CardContent>
      )}
    </Card>
  );
}

function SkeletonGroups() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="border-border bg-card shadow-none">
          <div className="px-5 py-4">
            <div className="h-5 w-64 animate-pulse rounded bg-muted" />
          </div>
        </Card>
      ))}
    </div>
  );
}

const GROUPS_PAGE_SIZE = 10;

export default function ClustersPage() {
  const [groups, setGroups] = useState<ClusterGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [groupPage, setGroupPage] = useState(0);

  useEffect(() => {
    api
      .getClusterGroups()
      .then((res) => setGroups(res.groups))
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Failed to load clusters",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const totalClusters = groups.reduce(
    (a, g) => a + g.subclusters.length,
    0,
  );

  const groupTotalPages = Math.max(1, Math.ceil(groups.length / GROUPS_PAGE_SIZE));
  const canGroupPrev = groupPage > 0;
  const canGroupNext = groupPage < groupTotalPages - 1;
  const pagedGroups = groups.slice(
    groupPage * GROUPS_PAGE_SIZE,
    (groupPage + 1) * GROUPS_PAGE_SIZE,
  );

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Boxes className="h-5 w-5 text-muted-foreground" />
            <h1 className="text-lg font-semibold tracking-tight">
              Task Clusters{" "}
              <InfoTooltip text="Discovered workflow types grouped by semantic similarity. Each cluster has an optimal execution path learned from successful runs." />
            </h1>
          </div>
          <p className="text-sm text-muted-foreground">
            {loading
              ? "Loading..."
              : error
                ? "Error"
                : `${groups.length} cluster${groups.length !== 1 ? "s" : ""}, ${totalClusters} variant${totalClusters !== 1 ? "s" : ""} discovered`}
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <SkeletonGroups />
      ) : groups.length === 0 ? (
        <Card className="border-border bg-card shadow-none">
          <CardContent className="py-12 text-center">
            <p className="text-sm text-muted-foreground">
              No clusters discovered yet
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {pagedGroups.map((group) => (
              <GroupSection key={group.name} group={group} />
            ))}
          </div>

          {groupTotalPages > 1 && (
            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Page {groupPage + 1} of {groupTotalPages}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setGroupPage((p) => p - 1)}
                  disabled={!canGroupPrev}
                  className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent/50 disabled:pointer-events-none disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  onClick={() => setGroupPage((p) => p + 1)}
                  disabled={!canGroupNext}
                  className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent/50 disabled:pointer-events-none disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  Hash,
  Activity,
  Zap,
  TrendingUp,
  ShieldCheck,
} from "lucide-react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  type ColumnDef,
  type Column,
  type SortingState,
  flexRender,
} from "@tanstack/react-table";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
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
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { DeltaCard } from "@/components/compare/delta-card";
import { ClusterPerformanceChart } from "@/components/clusters/cluster-performance-chart";
import { ClusterExecutionGraph } from "@/components/clusters/cluster-execution-graph";
import { OptimalPathGraph } from "@/components/clusters/optimal-path-graph";
import { CostLeakList } from "@/components/insights/cost-leak-list";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  formatDuration,
  formatPercent,
  formatNumber,
  formatCost,
  formatTimestamp,
} from "@/lib/format";
import type { ClusterDetailResponse, ClusterWorkflow, BottleneckTool } from "@/lib/types";

// ---------------------------------------------------------------------------
// Small shared helpers
// ---------------------------------------------------------------------------

function SectionHeader({ title, tooltip }: { title: string; tooltip?: string }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
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
      {tooltip ? (
        <InfoTooltip text={tooltip} />
      ) : null}
      <span className="font-mono tabular-nums text-foreground">{value}</span>
    </div>
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

function SortIcon({ isSorted }: { isSorted: false | "asc" | "desc" }) {
  if (isSorted === "asc")
    return <ArrowUp className="ml-1 inline h-3 w-3 text-foreground" />;
  if (isSorted === "desc")
    return <ArrowDown className="ml-1 inline h-3 w-3 text-foreground" />;
  return (
    <ArrowUpDown className="ml-1 inline h-3 w-3 text-muted-foreground opacity-40" />
  );
}

function SortableHeader({
  label,
  column,
}: {
  label: string;
  column: Column<ClusterWorkflow, unknown>;
}) {
  return (
    <button
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      className="flex items-center text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
    >
      {label}
      <SortIcon isSorted={column.getIsSorted()} />
    </button>
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ClusterDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const pathId = params.id;

  const [detail, setDetail] = useState<ClusterDetailResponse | null>(null);
  const [bottleneckTools, setBottleneckTools] = useState<BottleneckTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "timestamp", desc: true },
  ]);
  const [page, setPage] = useState(0);
  const pageSize = 15;

  useEffect(() => {
    if (!pathId) return;
    Promise.all([
      api.getClusterDetail(pathId),
      api.getClusterBottlenecks(pathId).catch(() => ({ tools: [] })),
    ])
      .then(([det, bn]) => {
        setDetail(det);
        setBottleneckTools(bn.tools);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Failed to load cluster detail",
        );
      })
      .finally(() => setLoading(false));
  }, [pathId]);

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------

  const columns = useMemo<ColumnDef<ClusterWorkflow>[]>(
    () => [
      {
        id: "status",
        accessorKey: "status",
        header: ({ column }) => (
          <SortableHeader label="Status" column={column} />
        ),
        cell: ({ row }) => <StatusDot status={row.original.status} />,
        size: 100,
      },
      {
        id: "task_description",
        accessorKey: "task_description",
        header: ({ column }) => (
          <SortableHeader label="Task" column={column} />
        ),
        cell: ({ row }) => (
          <span
            className="block max-w-xs truncate text-sm text-foreground"
            title={row.original.task_description ?? undefined}
          >
            {row.original.task_description ?? (
              <span className="text-muted-foreground">—</span>
            )}
          </span>
        ),
      },
      {
        id: "mode",
        accessorKey: "mode",
        header: ({ column }) => (
          <SortableHeader label="Mode" column={column} />
        ),
        cell: ({ row }) => {
          const isGuided = row.original.mode === "guided";
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
        },
        size: 110,
      },
      {
        id: "similarity",
        accessorKey: "similarity",
        header: ({ column }) => (
          <SortableHeader label="Similarity" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {(row.original.similarity * 100).toFixed(1)}%
          </span>
        ),
        size: 100,
      },
      {
        id: "duration_ms",
        accessorKey: "duration_ms",
        header: ({ column }) => (
          <SortableHeader label="Duration" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {formatDuration(row.original.duration_ms)}
          </span>
        ),
        size: 100,
      },
      {
        id: "steps",
        accessorKey: "steps",
        header: ({ column }) => (
          <SortableHeader label="Steps" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {row.original.steps ?? "—"}
          </span>
        ),
        size: 70,
      },
      {
        id: "cost_usd",
        accessorKey: "cost_usd",
        header: ({ column }) => (
          <SortableHeader label="Cost" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {formatCost(row.original.cost_usd)}
          </span>
        ),
        size: 90,
      },
      {
        id: "timestamp",
        accessorKey: "timestamp",
        header: ({ column }) => (
          <SortableHeader label="Timestamp" column={column} />
        ),
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground tabular-nums">
            {formatTimestamp(row.original.timestamp)}
          </span>
        ),
        size: 140,
        sortingFn: "datetime",
      },
    ],
    [],
  );

  const allWorkflows = useMemo(() => detail?.workflows ?? [], [detail]);
  const totalPages = Math.max(1, Math.ceil(allWorkflows.length / pageSize));
  const paginatedWorkflows = useMemo(
    () => allWorkflows.slice(page * pageSize, (page + 1) * pageSize),
    [allWorkflows, page, pageSize]
  );

  const coreRowModel = useMemo(() => getCoreRowModel<ClusterWorkflow>(), []);
  const sortedRowModel = useMemo(() => getSortedRowModel<ClusterWorkflow>(), []);

  const table = useReactTable({
    data: paginatedWorkflows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: coreRowModel,
    getSortedRowModel: sortedRowModel,
    autoResetAll: false,
  });

  // ---------------------------------------------------------------------------
  // Derived mode stats (safe, guarded by `detail` check at render time)
  // ---------------------------------------------------------------------------

  const exp = detail?.mode_stats.exploration;
  const guided = detail?.mode_stats.guided;

  const explorationStats =
    exp && exp.count > 0
      ? [
          { label: "Avg Duration", value: formatDuration(exp.avg_duration_ms) },
          { label: "Avg Steps", value: formatNumber(exp.avg_steps) },
          { label: "Success Rate", value: formatPercent(exp.success_rate) },
          { label: "Avg Cost", value: formatCost(exp.avg_cost_usd ?? null) },
          { label: "Workflows", value: formatNumber(exp.count) },
        ]
      : [];

  const guidedStats =
    guided && guided.count > 0
      ? [
          { label: "Avg Duration", value: formatDuration(guided.avg_duration_ms) },
          { label: "Avg Steps", value: formatNumber(guided.avg_steps) },
          { label: "Success Rate", value: formatPercent(guided.success_rate) },
          { label: "Avg Cost", value: formatCost(guided.avg_cost_usd ?? null) },
          { label: "Workflows", value: formatNumber(guided.count) },
        ]
      : [];

  const noModeData = explorationStats.length === 0 && guidedStats.length === 0;
  const hasBothModes = explorationStats.length > 0 && guidedStats.length > 0;

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
  const expCost = exp?.avg_cost_usd != null
    ? parseFloat((exp.avg_cost_usd * 100).toFixed(2)) : 0;
  const guidedCost = guided?.avg_cost_usd != null
    ? parseFloat((guided.avg_cost_usd * 100).toFixed(2)) : 0;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="p-6">
      {/* Back nav */}
      <div className="mb-4">
        <Link
          href="/clusters"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Clusters
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
      ) : detail ? (
        <div className="space-y-4">
          {/* Page header */}
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              {detail.task_cluster}
            </h1>
          </div>

          {/* Metadata strip */}
          <Card className="border-border bg-card py-4 shadow-none">
            <CardContent className="px-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <MetaChip
                  icon={Hash}
                  label="Workflows"
                  value={formatNumber(detail.workflows.length)}
                  tooltip="Number of workflows in this cluster that share a similar task embedding."
                />
                <MetaChip
                  icon={Clock}
                  label="Avg Duration"
                  value={formatDuration(detail.avg_duration_ms)}
                  tooltip="Mean duration across all workflows in this cluster."
                />
                <MetaChip
                  icon={Activity}
                  label="Avg Steps"
                  value={formatNumber(detail.avg_steps)}
                  tooltip="Average number of tool calls per workflow in this cluster."
                />
                <MetaChip
                  icon={TrendingUp}
                  label="Success Rate"
                  value={formatPercent(detail.success_rate)}
                  tooltip="Proportion of workflows in this cluster that completed successfully."
                />
                <MetaChip
                  icon={Zap}
                  label="Execution Count"
                  value={formatNumber(detail.execution_count)}
                  tooltip="Total number of individual tool calls across all workflows in this cluster."
                />
                {detail.avg_conformance != null && (
                  <MetaChip
                    icon={ShieldCheck}
                    label="Avg Conformance"
                    value={`${(detail.avg_conformance * 100).toFixed(0)}%`}
                    tooltip="Average conformance across all workflows in this cluster. Measures how closely each workflow's tool sequence matches the optimal path. 100% = every workflow followed the optimal path perfectly."
                  />
                )}
              </div>
            </CardContent>
          </Card>

          {/* Savings strip */}
          {hasBothModes && (
            <div className="grid grid-cols-3 gap-3 xl:grid-cols-5">
              <DeltaCard
                label="Success Rate"
                before={expSucc}
                after={guidedSucc}
                unit="%"
                lowerIsBetter={false}
              />
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
                label="Avg Cost"
                before={expCost}
                after={guidedCost}
                unit="¢"
                lowerIsBetter={true}
              />
              <DeltaCard
                label="API Calls"
                before={expSteps}
                after={guidedSteps}
                unit="calls"
                lowerIsBetter={true}
              />
            </div>
          )}

          {/* Execution Paths */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-4">
              <SectionHeader title="Execution Paths" tooltip="Optimal Path shows the learned best tool sequence. Execution Graph shows all observed tool transitions with edge thickness indicating frequency." />
              {detail.tool_sequence.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No tool sequence recorded yet.
                </p>
              ) : (
                <Tabs defaultValue="optimal">
                  <TabsList>
                    <TabsTrigger value="optimal">Optimal Path</TabsTrigger>
                    <TabsTrigger value="graph">Execution Graph</TabsTrigger>
                  </TabsList>
                  <TabsContent value="optimal">
                    <OptimalPathGraph
                      optimalSequence={detail.tool_sequence}
                    />
                  </TabsContent>
                  <TabsContent value="graph">
                    <ClusterExecutionGraph
                      pathId={detail.path_id}
                      optimalSequence={detail.tool_sequence}
                    />
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>

          {/* Performance chart */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-2">
              <SectionHeader title="Performance Over Time" tooltip="Scatter plot of workflow duration over time. Blue dots are exploration runs, green dots are guided runs. Trend lines show rolling averages." />
              <ClusterPerformanceChart workflows={detail.workflows} />
            </CardContent>
          </Card>

          {/* Mode comparison */}
          {noModeData ? (
            <Card className="border-border bg-card shadow-none">
              <CardContent className="px-4 py-6">
                <p className="text-center text-sm text-muted-foreground">
                  No mode-tagged workflows in this cluster yet.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {/* Exploration */}
              <Card className="border-border bg-card">
                <CardContent className="p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-blue-400" />
                    <span className="text-sm font-semibold text-blue-400">
                      Exploration
                    </span>
                  </div>
                  <div>
                    {explorationStats.length > 0 ? (
                      explorationStats.map((s) => (
                        <StatRow key={s.label} label={s.label} value={s.value} />
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No exploration runs yet.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Guided */}
              <Card className="border-border bg-card">
                <CardContent className="p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-sm font-semibold text-emerald-400">
                      Guided
                    </span>
                  </div>
                  <div>
                    {guidedStats.length > 0 ? (
                      guidedStats.map((s) => (
                        <StatRow key={s.label} label={s.label} value={s.value} />
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No guided runs yet.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Cost leaks */}
          {bottleneckTools.length > 0 && (
            <Card className="border-border bg-card shadow-none">
              <CardContent className="px-4 pt-4 pb-4">
                <SectionHeader
                  title="Cost Leaks"
                  tooltip="Tools in this cluster ranked by total cost. Amber-highlighted tools are called more than 2x per workflow on average, indicating potential redundancy."
                />
                <CostLeakList tools={bottleneckTools} />
              </CardContent>
            </Card>
          )}

          {/* Workflow runs table */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="p-0">
              <div className="px-4 pt-4">
                <SectionHeader title="Workflow Runs" tooltip="All workflow executions in this cluster, sortable by any column. Click a row to view its full trace." />
              </div>
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow
                      key={headerGroup.id}
                      className="border-border hover:bg-transparent"
                    >
                      {headerGroup.headers.map((header) => (
                        <TableHead
                          key={header.id}
                          style={{ width: header.getSize() }}
                          className="px-4 py-3"
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={columns.length}
                        className="py-12 text-center text-sm text-muted-foreground"
                      >
                        No workflow runs in this cluster
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <TableRow
                        key={row.id}
                        onClick={() =>
                          router.push(`/traces/${row.original.workflow_id}`)
                        }
                        className="cursor-pointer border-border transition-colors hover:bg-accent/30"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id} className="px-4 py-3">
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              {allWorkflows.length > pageSize && (
                <div className="flex items-center justify-between border-t border-border px-4 py-3">
                  <span className="text-xs text-muted-foreground">
                    {allWorkflows.length} workflows
                  </span>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="rounded px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      Page {page + 1} of {totalPages}
                    </span>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages - 1, p + 1))
                      }
                      disabled={page >= totalPages - 1}
                      className="rounded px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

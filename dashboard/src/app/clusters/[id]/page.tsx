"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  Hash,
  Activity,
  Zap,
  TrendingUp,
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
import { ClusterPerformanceChart } from "@/components/clusters/cluster-performance-chart";
import { api } from "@/lib/api";
import {
  formatDuration,
  formatPercent,
  formatNumber,
  formatCost,
  formatTimestamp,
} from "@/lib/format";
import type { ClusterDetailResponse, ClusterWorkflow } from "@/lib/types";

// ---------------------------------------------------------------------------
// Small shared helpers
// ---------------------------------------------------------------------------

function SectionHeader({ title }: { title: string }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
      {title}
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "timestamp", desc: true },
  ]);

  useEffect(() => {
    if (!pathId) return;
    api
      .getClusterDetail(pathId)
      .then(setDetail)
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

  const table = useReactTable({
    data: detail?.workflows ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // ---------------------------------------------------------------------------
  // Derived mode stats (safe, guarded by `detail` check at render time)
  // ---------------------------------------------------------------------------

  const exp = detail?.mode_stats.exploration;
  const guided = detail?.mode_stats.guided;

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
        { label: "Avg Duration", value: formatDuration(guided.avg_duration_ms) },
        { label: "Avg Steps", value: formatNumber(guided.avg_steps) },
        { label: "Success Rate", value: formatPercent(guided.success_rate) },
        { label: "Workflows", value: formatNumber(guided.count) },
      ]
    : [];

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
                />
                <MetaChip
                  icon={Clock}
                  label="Avg Duration"
                  value={formatDuration(detail.avg_duration_ms)}
                />
                <MetaChip
                  icon={Activity}
                  label="Avg Steps"
                  value={formatNumber(detail.avg_steps)}
                />
                <MetaChip
                  icon={TrendingUp}
                  label="Success Rate"
                  value={formatPercent(detail.success_rate)}
                />
                <MetaChip
                  icon={Zap}
                  label="Execution Count"
                  value={formatNumber(detail.execution_count)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Optimal Tool Sequence */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-4">
              <SectionHeader title="Optimal Tool Sequence" />
              {detail.tool_sequence.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No tool sequence recorded yet.
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {detail.tool_sequence.map((tool, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400"
                    >
                      <span className="font-mono tabular-nums text-[10px] opacity-60">
                        {i + 1}
                      </span>
                      <span>
                        {tool
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Performance chart */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="px-4 pt-4 pb-2">
              <SectionHeader title="Performance Over Time" />
              <ClusterPerformanceChart workflows={detail.workflows} />
            </CardContent>
          </Card>

          {/* Mode comparison */}
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

          {/* Workflow runs table */}
          <Card className="border-border bg-card shadow-none">
            <CardContent className="p-0">
              <div className="px-4 pt-4">
                <SectionHeader title="Workflow Runs" />
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
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
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
import type { TaskClusterSummary } from "@/lib/types";

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
  column: Column<TaskClusterSummary, unknown>;
}) {
  return (
    <button
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      className="flex items-center text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
    >
      {label}
      <SortIcon isSorted={column.getIsSorted()} />
    </button>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i} className="border-border hover:bg-transparent">
          <TableCell colSpan={6}>
            <div className="h-7 animate-pulse rounded bg-muted" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

export default function ClustersPage() {
  const router = useRouter();
  const [clusters, setClusters] = useState<TaskClusterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "workflow_count", desc: true },
  ]);

  useEffect(() => {
    api
      .getTaskClusters()
      .then((res) => {
        setClusters(res.clusters);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Failed to load clusters",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const columns = useMemo<ColumnDef<TaskClusterSummary>[]>(
    () => [
      {
        id: "task_cluster",
        accessorKey: "task_cluster",
        header: ({ column }) => (
          <SortableHeader label="Cluster" column={column} />
        ),
        cell: ({ row }) => (
          <span
            className="block max-w-xs truncate text-sm text-foreground"
            title={row.original.task_cluster}
          >
            {row.original.task_cluster}
          </span>
        ),
      },
      {
        id: "workflow_count",
        accessorKey: "workflow_count",
        header: ({ column }) => (
          <SortableHeader label="Workflows" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {row.original.workflow_count}
          </span>
        ),
        size: 100,
      },
      {
        id: "success_rate",
        accessorKey: "success_rate",
        header: ({ column }) => (
          <SortableHeader label="Success Rate" column={column} />
        ),
        cell: ({ row }) => (
          <SuccessRateBadge rate={row.original.success_rate} />
        ),
        size: 120,
      },
      {
        id: "avg_duration_ms",
        accessorKey: "avg_duration_ms",
        header: ({ column }) => (
          <SortableHeader label="Avg Duration" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {formatDuration(row.original.avg_duration_ms)}
          </span>
        ),
        size: 110,
      },
      {
        id: "optimal_steps",
        accessorFn: (row) => row.tool_sequence.length,
        header: ({ column }) => (
          <SortableHeader label="Optimal Steps" column={column} />
        ),
        cell: ({ row }) => (
          <span className="font-mono tabular-nums text-sm text-muted-foreground">
            {row.original.tool_sequence.length}
          </span>
        ),
        size: 110,
      },
      {
        id: "updated_at",
        accessorKey: "updated_at",
        header: ({ column }) => (
          <SortableHeader label="Updated" column={column} />
        ),
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground tabular-nums">
            {formatTimestamp(row.original.updated_at)}
          </span>
        ),
        size: 140,
        sortingFn: "datetime",
      },
    ],
    [],
  );

  const table = useReactTable({
    data: clusters,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Task Clusters{" "}
            <InfoTooltip text="Discovered workflow types grouped by semantic similarity. Each cluster has an optimal execution path learned from successful runs." />
          </h1>
          <p className="text-sm text-muted-foreground">
            {loading
              ? "Loading..."
              : error
                ? "Error"
                : `${clusters.length} cluster${clusters.length !== 1 ? "s" : ""} discovered`}
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <Card className="border-border bg-card shadow-none">
        <CardContent className="p-0">
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
              {loading ? (
                <SkeletonRows />
              ) : table.getRowModel().rows.length === 0 ? (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={columns.length}
                    className="py-12 text-center text-sm text-muted-foreground"
                  >
                    No clusters discovered yet
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    onClick={() =>
                      router.push(`/clusters/${row.original.path_id}`)
                    }
                    className="border-border cursor-pointer transition-colors hover:bg-accent/30"
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
  );
}

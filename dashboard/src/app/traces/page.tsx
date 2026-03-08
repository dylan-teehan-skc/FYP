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
import { ArrowUpDown, ArrowUp, ArrowDown, ListTree } from "lucide-react";
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
  const colorClass =
    status === "success"
      ? "bg-emerald-400"
      : status === "failure"
        ? "bg-red-400"
        : "bg-amber-400";
  return (
    <div className="flex items-center gap-2">
      <div className={`h-2 w-2 rounded-full ${colorClass} shrink-0`} />
      <span className="text-xs text-muted-foreground capitalize">{status}</span>
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
  column: Column<WorkflowListItem, unknown>;
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

const PAGE_SIZE = 25;

export default function TracesPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "timestamp", desc: true },
  ]);

  useEffect(() => {
    setLoading(true);
    api
      .getWorkflows(PAGE_SIZE, page * PAGE_SIZE)
      .then((res) => {
        setWorkflows(res.workflows);
        setTotal(res.total);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Failed to load workflows",
        );
      })
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const canPrev = page > 0;
  const canNext = page < totalPages - 1;

  const columns = useMemo<ColumnDef<WorkflowListItem>[]>(
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
            title={row.original.task_description}
          >
            {row.original.task_description}
          </span>
        ),
      },
      {
        id: "mode",
        accessorKey: "mode",
        header: ({ column }) => (
          <SortableHeader label="Mode" column={column} />
        ),
        cell: ({ row }) => <ModeBadge mode={row.original.mode} />,
        size: 120,
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
            {row.original.steps}
          </span>
        ),
        size: 70,
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

  const coreRowModel = useMemo(() => getCoreRowModel<WorkflowListItem>(), []);
  const sortedRowModel = useMemo(() => getSortedRowModel<WorkflowListItem>(), []);

  const table = useReactTable({
    data: workflows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: coreRowModel,
    getSortedRowModel: sortedRowModel,
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ListTree className="h-5 w-5 text-muted-foreground" />
            <h1 className="text-lg font-semibold tracking-tight">
              Workflow Traces{" "}
              <InfoTooltip text="Every workflow execution captured by the SDK. Each row is one agent run — click to see the full step-by-step trace, Gantt timeline, and conformance against the optimal path." />
            </h1>
          </div>
          <p className="text-sm text-muted-foreground">
            {loading
              ? "Loading..."
              : error
                ? "Error loading workflows"
                : `${total} workflow${total !== 1 ? "s" : ""} recorded`}
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
                    No workflows recorded yet
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    onClick={() =>
                      router.push(`/traces/${row.original.workflow_id}`)
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

      {!loading && !error && totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Page {page + 1} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={!canPrev}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent/50 disabled:pointer-events-none disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!canNext}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent/50 disabled:pointer-events-none disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

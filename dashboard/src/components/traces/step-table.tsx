"use client";

import { useState, Fragment } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDuration } from "@/lib/format";
import type { EventOut } from "@/lib/types";

interface StepTableProps {
  events: EventOut[];
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "success"
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      : status === "failure"
        ? "text-red-400 bg-red-500/10 border-red-500/20"
        : "text-amber-400 bg-amber-500/10 border-amber-500/20";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium ${cls}`}
    >
      {status}
    </span>
  );
}

function JsonBlock({ value }: { value: Record<string, unknown> }) {
  const isEmpty =
    value === null ||
    value === undefined ||
    (typeof value === "object" && Object.keys(value).length === 0);

  if (isEmpty) {
    return <span className="text-muted-foreground italic text-xs">empty</span>;
  }

  return (
    <pre className="overflow-x-auto rounded bg-zinc-950 p-3 text-xs text-zinc-300 font-mono leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function ExpandedRow({ event }: { event: EventOut }) {
  return (
    <tr className="bg-zinc-900/60">
      <td colSpan={6} className="px-4 py-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Parameters
            </p>
            <JsonBlock value={event.tool_parameters} />
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Response
            </p>
            <JsonBlock value={event.tool_response} />
          </div>
        </div>
        {event.llm_reasoning && (
          <div className="mt-3">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Reasoning
            </p>
            <p className="text-xs text-zinc-400 leading-relaxed bg-zinc-950 rounded p-3 font-mono">
              {event.llm_reasoning}
            </p>
          </div>
        )}
        {event.error_message && (
          <div className="mt-3">
            <p className="mb-1.5 text-xs font-medium text-red-400 uppercase tracking-wider">
              Error
            </p>
            <p className="text-xs text-red-300 bg-red-950/30 rounded p-3 font-mono">
              {event.error_message}
            </p>
          </div>
        )}
      </td>
    </tr>
  );
}

export function StepTable({ events }: StepTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleRow(eventId: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  }

  if (events.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No events in trace.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="border-border hover:bg-transparent">
          <TableHead className="w-8" />
          <TableHead className="w-12 text-xs text-muted-foreground font-medium">
            #
          </TableHead>
          <TableHead className="text-xs text-muted-foreground font-medium">
            Tool
          </TableHead>
          <TableHead className="text-xs text-muted-foreground font-medium text-right">
            Duration
          </TableHead>
          <TableHead className="text-xs text-muted-foreground font-medium">
            Status
          </TableHead>
          <TableHead className="text-xs text-muted-foreground font-medium text-right">
            Tokens
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {events.map((event) => {
          const isExpanded = expandedIds.has(event.event_id);
          const hasDetail =
            Object.keys(event.tool_parameters ?? {}).length > 0 ||
            Object.keys(event.tool_response ?? {}).length > 0 ||
            !!event.llm_reasoning ||
            !!event.error_message;

          return (
            <Fragment key={event.event_id}>
              <TableRow
                onClick={() => hasDetail && toggleRow(event.event_id)}
                className={`border-border transition-colors ${hasDetail ? "cursor-pointer hover:bg-accent/30" : ""}`}
              >
                <TableCell className="w-8 text-muted-foreground">
                  {hasDetail ? (
                    isExpanded ? (
                      <ChevronDown className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" />
                    )
                  ) : null}
                </TableCell>
                <TableCell className="font-mono tabular-nums text-sm text-muted-foreground">
                  {event.step_number}
                </TableCell>
                <TableCell>
                  <span className="text-sm text-foreground font-medium">
                    {event.tool_name ?? (
                      <span className="text-muted-foreground italic text-xs">
                        {event.activity}
                      </span>
                    )}
                  </span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {event.agent_role}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-sm text-muted-foreground">
                  {formatDuration(event.duration_ms)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={event.status} />
                </TableCell>
                <TableCell className="text-right">
                  {event.llm_prompt_tokens > 0 ||
                  event.llm_completion_tokens > 0 ? (
                    <span className="font-mono tabular-nums text-xs text-muted-foreground">
                      <span className="text-zinc-400">
                        {event.llm_prompt_tokens.toLocaleString()}
                      </span>
                      <span className="text-zinc-600 mx-0.5">+</span>
                      <span className="text-zinc-400">
                        {event.llm_completion_tokens.toLocaleString()}
                      </span>
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-xs">-</span>
                  )}
                </TableCell>
              </TableRow>
              {isExpanded && <ExpandedRow event={event} />}
            </Fragment>
          );
        })}
      </TableBody>
    </Table>
  );
}

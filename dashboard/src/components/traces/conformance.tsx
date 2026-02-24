"use client";

import type { EventOut, OptimalPath } from "@/lib/types";
import { findBestMatch } from "@/lib/path-matching";

interface ConformanceProps {
  events: EventOut[];
  optimalPaths: OptimalPath[];
}

function shortenToolName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Conformance({ events, optimalPaths }: ConformanceProps) {
  const toolEvents = events.filter((e) => e.tool_name !== null);
  const toolSequence = toolEvents.map((e) => e.tool_name as string);

  const match = findBestMatch(toolSequence, optimalPaths);

  if (toolSequence.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">
          Conformance
        </p>
        <p className="text-sm text-muted-foreground">No tool calls in trace.</p>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">
          Conformance
        </p>
        <p className="text-sm text-muted-foreground">
          No optimal path available for comparison.
        </p>
      </div>
    );
  }

  const { path: bestPath, alignment } = match;
  const matchCount = alignment.filter((a) => a.status === "match").length;
  const conformancePct =
    alignment.length > 0
      ? Math.round((matchCount / alignment.length) * 100)
      : 0;

  const pctColor =
    conformancePct >= 80
      ? "text-emerald-400"
      : conformancePct >= 50
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="flex items-baseline gap-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Conformance
          </p>
          <span className="text-xs text-muted-foreground/60">
            vs. &ldquo;{bestPath.task_cluster}&rdquo;
          </span>
        </div>
        <span className={`font-mono text-sm tabular-nums font-semibold ${pctColor}`}>
          {conformancePct}%
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {alignment.map((step, index) => {
          const bg =
            step.status === "match"
              ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
              : step.status === "deviation"
                ? "bg-amber-500/15 border-amber-500/30 text-amber-400"
                : "bg-zinc-500/15 border-zinc-500/30 text-muted-foreground";

          return (
            <div
              key={index}
              title={
                step.status === "match"
                  ? `Step ${index + 1}: matches optimal`
                  : step.status === "deviation"
                    ? `Step ${index + 1}: deviates — optimal expects "${bestPath.tool_sequence[index] ?? "end"}"`
                    : `Step ${index + 1}: extra step beyond optimal path`
              }
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${bg}`}
            >
              <span className="font-mono tabular-nums text-[10px] opacity-60">
                {index + 1}
              </span>
              <span>{shortenToolName(step.toolName)}</span>
            </div>
          );
        })}
      </div>

      {bestPath.tool_sequence.length > toolSequence.length && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          <span className="text-xs text-muted-foreground self-center">
            Optimal continues:
          </span>
          {bestPath.tool_sequence.slice(toolSequence.length).map((tool, index) => (
            <div
              key={index}
              className="flex items-center gap-1.5 rounded-full border border-zinc-600/30 bg-zinc-600/10 px-2.5 py-0.5 text-xs font-medium text-zinc-500"
            >
              <span className="font-mono tabular-nums text-[10px] opacity-60">
                {toolSequence.length + index + 1}
              </span>
              <span>{shortenToolName(tool)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center gap-4 border-t border-border pt-3">
        <LegendItem color="bg-emerald-400" label="Matches optimal" />
        <LegendItem color="bg-amber-400" label="Deviates" />
        <LegendItem color="bg-zinc-500" label="Extra step" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-2 w-2 rounded-full ${color}`} />
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatDelta } from "@/lib/format";

interface DeltaCardProps {
  label: string;
  before: number;
  after: number;
  unit: string;
  lowerIsBetter: boolean;
  hasData?: boolean;
}

export function DeltaCard({
  label,
  before,
  after,
  unit,
  lowerIsBetter,
  hasData = true,
}: DeltaCardProps) {
  const noGuided = !hasData;

  const { label: deltaLabel, pct, improved: rawImproved } = noGuided
    ? { label: "—", pct: 0, improved: false }
    : formatDelta(before, after);

  // "improved" from formatDelta means before > after (value went down).
  // For lowerIsBetter metrics that is genuinely good; for higherIsBetter it is bad.
  const isGood = lowerIsBetter ? rawImproved : !rawImproved;
  const accentClass = noGuided || pct === 0
    ? "text-muted-foreground"
    : isGood ? "text-emerald-400" : "text-red-400";
  const badgeBg = noGuided || pct === 0
    ? "bg-muted text-muted-foreground"
    : isGood
    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
    : "bg-red-500/15 text-red-400 border border-red-500/25";

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-5">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <div className="mb-2 flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold tabular-nums text-foreground">
            {before}
          </span>
          <span className="text-sm text-muted-foreground">{unit}</span>
          <span className="mx-1 text-muted-foreground">→</span>
          {noGuided ? (
            <span className="font-mono text-2xl font-semibold tabular-nums text-muted-foreground">
              -
            </span>
          ) : (
            <>
              <span className={`font-mono text-2xl font-semibold tabular-nums ${accentClass}`}>
                {after}
              </span>
              <span className="text-sm text-muted-foreground">{unit}</span>
            </>
          )}
        </div>
        <div className="mt-3">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-sm font-semibold tabular-nums ${badgeBg}`}
          >
            {deltaLabel}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

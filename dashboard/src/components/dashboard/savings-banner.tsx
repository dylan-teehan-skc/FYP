"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatDuration, formatPercent } from "@/lib/format";
import type { SavingsResponse } from "@/lib/types";
import { TrendingDown } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";

export function SavingsBanner() {
  const [data, setData] = useState<SavingsResponse | null>(null);

  useEffect(() => {
    api.getSavings().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="p-4">
          <div className="h-16 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  const hasGuidedData = data.guided_count > 0;

  const deltas = [
    {
      label: "Duration",
      value: formatDuration(data.time_saved_ms),
      pct: data.pct_duration_improvement,
      suffix: "faster",
    },
    {
      label: "Steps",
      value: `${data.pct_steps_improvement.toFixed(0)}%`,
      pct: data.pct_steps_improvement,
      suffix: "fewer steps",
    },
    {
      label: "Success Rate",
      value: formatPercent(data.pct_success_improvement / 100),
      pct: data.pct_success_improvement,
      suffix: "improvement",
    },
  ];

  return (
    <Card className={hasGuidedData ? "border-emerald-500/20 bg-emerald-500/5" : "border-border bg-card"}>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <TrendingDown className={`h-4 w-4 ${hasGuidedData ? "text-emerald-400" : "text-muted-foreground"}`} />
          <span className={`text-sm font-medium ${hasGuidedData ? "text-emerald-400" : "text-muted-foreground"}`}>
            Optimization Impact
          </span>
          <InfoTooltip text="Percentage improvement in guided mode compared to exploration mode. As the system learns optimal paths, these numbers improve." />
        </div>
        {hasGuidedData ? (
          <div className="grid grid-cols-3 gap-6">
            {deltas.map((d) => (
              <div key={d.label}>
                <p className="text-xs text-muted-foreground">{d.label}</p>
                <div className="flex items-baseline gap-1.5">
                  <span className="font-mono text-xl font-semibold tabular-nums text-emerald-400">
                    {d.pct > 0 ? `↓${d.pct.toFixed(0)}%` : "-"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {d.suffix}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Awaiting guided mode data. Run the analysis pipeline and then execute
            more workflows to see optimization impact.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

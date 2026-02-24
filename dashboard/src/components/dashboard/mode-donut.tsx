"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ModeDistribution } from "@/lib/types";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { InfoTooltip } from "@/components/ui/info-tooltip";

const COLORS = {
  guided: "#34d399",
  exploration: "#60a5fa",
};

export function ModeDonut() {
  const [data, setData] = useState<ModeDistribution | null>(null);

  useEffect(() => {
    api.getModeDistribution().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="p-4">
          <div className="h-48 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  const chartData = [
    { name: "Guided", value: data.guided, color: COLORS.guided },
    { name: "Exploration", value: data.exploration, color: COLORS.exploration },
  ];

  const guidedPct =
    data.total > 0 ? ((data.guided / data.total) * 100).toFixed(0) : "0";

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Mode Distribution{" "}
          <InfoTooltip text="Breakdown of workflows by execution mode. Exploration runs discover paths freely; Guided runs follow the historically optimal path. A higher guided ratio indicates the system is actively optimizing." />
        </p>
        <div className="flex items-center gap-4">
          <div className="relative h-32 w-32">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={36}
                  outerRadius={56}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-lg font-semibold tabular-nums text-foreground">
                {guidedPct}%
              </span>
              <span className="text-[10px] text-muted-foreground">guided</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-sm bg-emerald-400" />
              <span className="text-sm text-muted-foreground">Guided</span>
              <span className="font-mono text-sm tabular-nums text-foreground">
                {data.guided}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-sm bg-blue-400" />
              <span className="text-sm text-muted-foreground">Exploration</span>
              <span className="font-mono text-sm tabular-nums text-foreground">
                {data.exploration}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

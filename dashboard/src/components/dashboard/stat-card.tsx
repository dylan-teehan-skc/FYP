"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  subtitle?: string;
  accentColor?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  subtitle,
  accentColor = "text-emerald-400",
}: StatCardProps) {
  return (
    <Card className="relative overflow-hidden border-border bg-card">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            <p
              className={`font-mono text-2xl font-semibold tabular-nums ${accentColor}`}
            >
              {value}
            </p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="rounded-md border border-border p-1.5">
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

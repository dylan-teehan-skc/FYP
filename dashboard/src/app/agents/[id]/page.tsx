"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Radio, Clock, Hash, Activity, DollarSign } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ChatView } from "@/components/agents/chat-view";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api";
import {
  formatDuration,
  formatTimestamp,
  formatCost,
  formatNumber,
} from "@/lib/format";
import type { TraceOut, EventOut } from "@/lib/types";

function MetaChip({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums text-foreground">{value}</span>
    </div>
  );
}

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

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "success"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
      : status === "failure"
        ? "border-red-500/30 bg-red-500/10 text-red-400"
        : "border-blue-500/30 bg-blue-500/10 text-blue-400";
  return (
    <Badge variant="outline" className={cls}>
      {status === "in_progress" ? "live" : status}
    </Badge>
  );
}

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const workflowId = params.id;

  const [trace, setTrace] = useState<TraceOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    if (!workflowId) return;
    api
      .getWorkflowTrace(workflowId)
      .then((data) => {
        setTrace(data);
        const hasComplete = data.events.some(
          (e) =>
            e.activity === "workflow:complete" || e.activity === "workflow:fail",
        );
        setIsLive(!hasComplete);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load trace");
      })
      .finally(() => setLoading(false));
  }, [workflowId]);

  const { events: wsEvents } = useWebSocket({
    workflowId,
    enabled: isLive,
  });

  // Merge REST + WS events, deduplicate by event_id
  const allEvents: EventOut[] = (() => {
    const restEvents = trace?.events ?? [];
    const seen = new Set(restEvents.map((e) => e.event_id));
    const newEvents = wsEvents.filter((e) => !seen.has(e.event_id));
    return [...restEvents, ...newEvents];
  })();

  // Stop live mode when we see completion via WebSocket
  useEffect(() => {
    if (
      wsEvents.some(
        (e) =>
          e.activity === "workflow:complete" || e.activity === "workflow:fail",
      )
    ) {
      setIsLive(false);
    }
  }, [wsEvents]);

  const totalDurationMs = allEvents.reduce(
    (sum, e) => sum + e.duration_ms,
    0,
  );
  const totalCost = allEvents.reduce((sum, e) => sum + (e.cost_usd ?? 0), 0);
  const totalTokens = allEvents.reduce(
    (sum, e) => sum + e.llm_prompt_tokens + e.llm_completion_tokens,
    0,
  );
  const toolSteps = allEvents.filter((e) =>
    e.activity.startsWith("tool_call:"),
  ).length;

  const overallStatus = allEvents.some((e) => e.status === "failure")
    ? "failure"
    : isLive
      ? "in_progress"
      : "success";

  const mode = allEvents.some((e) => e.activity === "optimize:guided")
    ? "guided"
    : "exploration";

  return (
    <div className="p-6">
      <div className="mb-4">
        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Agent Chat
        </Link>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="h-6 w-80 animate-pulse rounded bg-muted" />
          <div className="h-32 animate-pulse rounded bg-muted" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-6">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                {trace?.task_description || "Agent Conversation"}
              </h1>
              <p className="mt-0.5 font-mono text-xs text-muted-foreground tabular-nums">
                {workflowId}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {isLive && (
                <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5">
                  <Radio className="h-3 w-3 text-emerald-400 animate-pulse" />
                  <span className="text-[10px] font-medium text-emerald-400">
                    LIVE
                  </span>
                </div>
              )}
              <StatusBadge status={overallStatus} />
              <ModeBadge mode={mode} />
            </div>
          </div>

          {/* Metadata strip */}
          <Card className="border-border bg-card py-4 shadow-none">
            <CardContent className="px-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <MetaChip
                  icon={Hash}
                  label="Steps"
                  value={formatNumber(toolSteps)}
                />
                <MetaChip
                  icon={Clock}
                  label="Duration"
                  value={formatDuration(totalDurationMs)}
                />
                <MetaChip
                  icon={Activity}
                  label="Tokens"
                  value={formatNumber(totalTokens)}
                />
                <MetaChip
                  icon={DollarSign}
                  label="Cost"
                  value={formatCost(totalCost)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Chat view */}
          <ChatView events={allEvents} isLive={isLive} />
        </div>
      )}
    </div>
  );
}

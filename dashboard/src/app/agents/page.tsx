"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MessageSquare, Radio, Bot, ChevronRight } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import type { WorkflowListItem } from "@/lib/types";

function LivePulse() {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5">
      <Radio className="h-2.5 w-2.5 text-emerald-400 animate-pulse" />
      <span className="text-[10px] font-medium text-emerald-400">LIVE</span>
    </div>
  );
}

function ConversationCard({ workflow }: { workflow: WorkflowListItem }) {
  const router = useRouter();
  const isLive = workflow.status === "in_progress";
  const isFailed = workflow.status === "failure";

  return (
    <button
      onClick={() => router.push(`/agents/${workflow.workflow_id}`)}
      className="w-full text-left group"
    >
      <div
        className={`relative rounded-lg border p-4 transition-all cursor-pointer hover:scale-[1.01] hover:shadow-md hover:border-foreground/20 ${
          isLive
            ? "border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50"
            : isFailed
              ? "border-red-500/20 bg-card hover:border-red-500/40"
              : "border-border bg-card"
        }`}
      >
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
              isLive
                ? "bg-emerald-500/15 text-emerald-400"
                : isFailed
                  ? "bg-red-500/15 text-red-400"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            <Bot className="h-4 w-4" />
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground truncate">
                {workflow.task_description || "Agent Conversation"}
              </span>
              {isLive && <LivePulse />}
            </div>

            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span>{formatTimestamp(workflow.timestamp)}</span>
              <span>·</span>
              {!isLive && (
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${
                    isFailed
                      ? "border-red-500/30 bg-red-500/10 text-red-400"
                      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  }`}
                >
                  {isFailed ? "Failed" : "Success"}
                </Badge>
              )}
              <Badge
                variant="outline"
                className={`text-[10px] px-1.5 py-0 ${
                  workflow.mode === "guided"
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    : "border-blue-500/30 bg-blue-500/10 text-blue-400"
                }`}
              >
                {workflow.mode === "guided" ? "Guided" : "Exploration"}
              </Badge>
              {workflow.steps != null && (
                <>
                  <span>·</span>
                  <span>{workflow.steps} steps</span>
                </>
              )}
            </div>
          </div>

          {/* Arrow */}
          <ChevronRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-foreground transition-colors shrink-0 mt-1" />
        </div>
      </div>
    </button>
  );
}

function SkeletonCards() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
              <div className="h-3 w-1/3 rounded bg-muted animate-pulse" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

const PAGE_SIZE = 25;

export default function AgentsPage() {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [activeWorkflows, setActiveWorkflows] = useState<WorkflowListItem[]>(
    [],
  );
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getWorkflows(PAGE_SIZE, page * PAGE_SIZE),
      api.getActiveWorkflows().catch(() => ({ workflows: [], total: 0 })),
    ])
      .then(([recent, active]) => {
        setWorkflows(recent.workflows);
        setTotal(recent.total);
        setActiveWorkflows(active.workflows);
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

  // Merge: active workflows first (page 0 only), then completed (deduped)
  const activeIds = new Set(activeWorkflows.map((w) => w.workflow_id));
  const allWorkflows =
    page === 0
      ? [
          ...activeWorkflows,
          ...workflows.filter((w) => !activeIds.has(w.workflow_id)),
        ]
      : workflows;

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold tracking-tight">
            Agent Chat{" "}
            <InfoTooltip text="Watch agent conversations in real-time or replay completed workflows. Click a conversation to see full agent reasoning, tool calls, and LLM prompts." />
          </h1>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          {loading
            ? "Loading conversations..."
            : error
              ? "Error loading conversations"
              : `${total} conversation${total !== 1 ? "s" : ""}`}
          {activeWorkflows.length > 0 && !loading && (
            <span className="ml-2 inline-flex items-center gap-1">
              <Radio className="h-3 w-3 text-emerald-400 animate-pulse" />
              <span className="text-emerald-400">
                {activeWorkflows.length} live
              </span>
            </span>
          )}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <SkeletonCards />
      ) : allWorkflows.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-12 text-center">
          <Bot className="mx-auto h-8 w-8 text-muted-foreground/50 mb-3" />
          <p className="text-sm text-muted-foreground">
            No agent conversations yet
          </p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Run a workflow to see agent conversations here
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {allWorkflows.map((wf) => (
            <ConversationCard key={wf.workflow_id} workflow={wf} />
          ))}
        </div>
      )}

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

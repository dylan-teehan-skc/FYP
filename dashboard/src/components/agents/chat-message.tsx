"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  Brain,
  Play,
  CheckCircle2,
  XCircle,
  Zap,
  FileText,
  Route,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDuration, formatTimestamp } from "@/lib/format";
import type { EventOut } from "@/lib/types";

function JsonBlock({ data }: { data: Record<string, unknown> }) {
  const text = JSON.stringify(data, null, 2);
  if (text === "{}" || text === "null") return null;
  return (
    <pre className="mt-1.5 max-h-48 overflow-auto rounded bg-zinc-900/60 p-2 text-[11px] leading-relaxed text-zinc-300 font-mono">
      {text}
    </pre>
  );
}

function CollapsibleSection({
  label,
  icon: Icon,
  children,
  defaultOpen = false,
}: {
  label: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 hover:text-muted-foreground transition-colors"
      >
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <Icon className="h-3 w-3" />
        {label}
      </button>
      {open && <div className="mt-1.5">{children}</div>}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "success")
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
  return <XCircle className="h-3.5 w-3.5 text-red-400" />;
}

/** Extract the guided context block from an LLM prompt string. */
function extractGuidedContext(prompt: string): string | null {
  const markers = [
    "OPTIMIZATION HINT —",
    "OPTIMIZATION HINT:",
    "RECOMMENDED PATH:",
    "IMPORTANT — VALIDATED OPTIMAL PATH:",
    "VALIDATED PATHS for this task type:",
  ];
  let idx = -1;
  for (const m of markers) {
    idx = prompt.indexOf(m);
    if (idx !== -1) break;
  }
  if (idx === -1) return null;
  const endMarkers = ["</context>", "\n\nYou are", "\n\n---"];
  let endIdx = prompt.length;
  for (const m of endMarkers) {
    const pos = prompt.indexOf(m, idx);
    if (pos !== -1 && pos < endIdx) endIdx = pos;
  }
  return prompt.slice(idx, endIdx).trim();
}

interface ChatMessageProps {
  event: EventOut;
  /** All events in the conversation — used to extract guided context for display */
  allEvents?: EventOut[];
}

export function ChatMessage({ event, allEvents }: ChatMessageProps) {
  const { activity } = event;

  // workflow:start
  if (activity === "workflow:start") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border/50 bg-zinc-900/30 px-4 py-2.5">
        <Play className="h-3.5 w-3.5 text-blue-400" />
        <span className="text-xs font-medium text-blue-400">
          Workflow Started
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/50 tabular-nums">
          {formatTimestamp(event.timestamp)}
        </span>
      </div>
    );
  }

  // workflow:complete
  if (activity === "workflow:complete") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5">
        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
        <span className="text-xs font-medium text-emerald-400">
          Workflow Complete
        </span>
        {event.duration_ms > 0 && (
          <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
            {formatDuration(event.duration_ms)}
          </span>
        )}
        <span className="ml-auto text-[10px] text-muted-foreground/50 tabular-nums">
          {formatTimestamp(event.timestamp)}
        </span>
      </div>
    );
  }

  // workflow:fail
  if (activity === "workflow:fail") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <XCircle className="h-3.5 w-3.5 text-red-400" />
          <span className="text-xs font-medium text-red-400">
            Workflow Failed
          </span>
          {event.duration_ms > 0 && (
            <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
              {formatDuration(event.duration_ms)}
            </span>
          )}
          <span className="ml-auto text-[10px] text-muted-foreground/50 tabular-nums">
            {formatTimestamp(event.timestamp)}
          </span>
        </div>
        {event.error_message && (
          <p className="mt-1.5 text-xs text-red-400/80">
            {event.error_message}
          </p>
        )}
      </div>
    );
  }

  // optimize:guided — show injected optimal path context
  if (activity === "optimize:guided") {
    const firstToolCall = allEvents?.find(
      (e) => e.activity.startsWith("tool_call:") && e.llm_prompt,
    );
    const guidedContext = firstToolCall?.llm_prompt
      ? extractGuidedContext(firstToolCall.llm_prompt)
      : null;

    const isDecisionTree =
      guidedContext?.includes("├──") || guidedContext?.includes("└──");
    const headerText = isDecisionTree
      ? "Guided Mode — Decision Tree Injected"
      : "Guided Mode — Optimal Path Injected";
    const sectionLabel = isDecisionTree
      ? "Injected Decision Tree"
      : "Injected Optimal Path";

    return (
      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
        <div className="flex items-center gap-2">
          <Zap className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-emerald-400">
            {headerText}
          </span>
          <Badge
            variant="outline"
            className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[10px]"
          >
            Optimized
          </Badge>
        </div>
        {guidedContext && (
          <CollapsibleSection
            label={sectionLabel}
            icon={Route}
            defaultOpen
          >
            <pre className="max-h-48 overflow-auto rounded bg-emerald-950/40 border border-emerald-500/10 p-2.5 text-[11px] leading-relaxed text-emerald-300/80 font-mono whitespace-pre-wrap">
              {guidedContext}
            </pre>
          </CollapsibleSection>
        )}
      </div>
    );
  }

  // optimize:exploration
  if (activity === "optimize:exploration") {
    return (
      <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Zap className="h-3.5 w-3.5 text-blue-400" />
          <span className="text-xs font-medium text-blue-400">
            Exploration Mode — No Optimal Path Available
          </span>
        </div>
      </div>
    );
  }

  // tool_call:* — the main chat message
  if (activity.startsWith("tool_call:")) {
    const guidedHint = event.llm_prompt
      ? extractGuidedContext(event.llm_prompt)
      : null;

    return (
      <div className="space-y-2">
        {/* Reasoning bubble */}
        {event.llm_reasoning && (
          <div className="rounded-lg bg-zinc-800/40 px-4 py-3">
            <div className="mb-1.5 flex items-center gap-1.5">
              <Brain className="h-3.5 w-3.5 text-violet-400" />
              <span className="text-[10px] font-medium uppercase tracking-wider text-violet-400">
                Reasoning
              </span>
              <span className="ml-auto text-[10px] text-muted-foreground/40 tabular-nums">
                Step {event.step_number}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-zinc-300 whitespace-pre-wrap">
              {event.llm_reasoning}
            </p>
          </div>
        )}

        {/* Tool call card */}
        <div className="rounded-lg border border-border bg-card px-4 py-3">
          <div className="flex items-center gap-2">
            <Wrench className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-sm font-medium text-foreground">
              {event.tool_name}
            </span>
            <StatusIcon status={event.status} />
            <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
              {formatDuration(event.duration_ms)}
            </span>
            <span className="ml-auto text-[10px] text-muted-foreground/50 tabular-nums">
              {formatTimestamp(event.timestamp)}
            </span>
          </div>

          {/* Parameters */}
          {event.tool_parameters &&
            Object.keys(event.tool_parameters).length > 0 && (
              <CollapsibleSection label="Parameters" icon={ChevronRight} defaultOpen>
                <JsonBlock data={event.tool_parameters} />
              </CollapsibleSection>
            )}

          {/* Response */}
          {event.tool_response &&
            Object.keys(event.tool_response).length > 0 && (
              <CollapsibleSection label="Response" icon={ChevronRight} defaultOpen>
                <JsonBlock data={event.tool_response} />
              </CollapsibleSection>
            )}

          {/* Error */}
          {event.error_message && (
            <p className="mt-2 rounded bg-red-500/10 px-2 py-1 text-xs text-red-400">
              {event.error_message}
            </p>
          )}

          {/* Injected guided context (shown separately for visibility) */}
          {guidedHint && (
            <CollapsibleSection label="Injected Optimization Hint" icon={Route}>
              <pre className="max-h-48 overflow-auto rounded bg-emerald-950/40 border border-emerald-500/10 p-2.5 text-[11px] leading-relaxed text-emerald-300/80 font-mono whitespace-pre-wrap">
                {guidedHint}
              </pre>
            </CollapsibleSection>
          )}

          {/* Full LLM prompt (collapsible) */}
          {event.llm_prompt && (
            <CollapsibleSection label="Full LLM Prompt" icon={FileText}>
              <pre className="max-h-64 overflow-auto rounded bg-zinc-900/60 p-2 text-[11px] leading-relaxed text-zinc-400 font-mono whitespace-pre-wrap">
                {event.llm_prompt}
              </pre>
            </CollapsibleSection>
          )}

          {/* LLM metadata */}
          {(event.llm_prompt_tokens > 0 || event.cost_usd > 0) && (
            <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground/40 tabular-nums font-mono">
              {event.llm_model && <span>{event.llm_model}</span>}
              {event.llm_prompt_tokens > 0 && (
                <span>
                  {event.llm_prompt_tokens + event.llm_completion_tokens} tokens
                </span>
              )}
              {event.cost_usd > 0 && (
                <span>${event.cost_usd.toFixed(4)}</span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Fallback for unknown event types
  return (
    <div className="rounded-lg border border-border/30 bg-zinc-900/20 px-4 py-2.5">
      <span className="text-xs text-muted-foreground">{activity}</span>
    </div>
  );
}

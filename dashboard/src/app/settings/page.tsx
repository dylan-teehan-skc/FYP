"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { AnalyticsSummary } from "@/lib/types";
import { Database, Activity, Server, Play, FlaskConical, Loader2 } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";

const THRESHOLDS = [
  {
    label: "Similarity Threshold",
    value: "0.85",
    description: "Minimum cosine similarity for semantic path matching",
  },
  {
    label: "Min Executions",
    value: "30",
    description: "Minimum workflow executions before guided mode activates",
  },
  {
    label: "Min Success Rate",
    value: "0.85",
    description: "Minimum historical success rate to trust an optimal path",
  },
  {
    label: "NED Threshold",
    value: "0.55",
    description:
      "Normalized edit distance cutoff for trace sub-clustering (HAC)",
  },
  {
    label: "Bottleneck Threshold",
    value: "40%",
    description: "Duration percentage to flag a tool as a bottleneck",
  },
];

function HealthIndicator({
  label,
  icon: Icon,
  status,
}: {
  label: string;
  icon: typeof Database;
  status: "online" | "offline" | "checking";
}) {
  const color =
    status === "online"
      ? "bg-emerald-400"
      : status === "offline"
        ? "bg-red-400"
        : "bg-amber-400 animate-pulse";
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm">{label}</span>
      <div className="ml-auto flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${color}`} />
        <span className="text-xs text-muted-foreground capitalize">
          {status}
        </span>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [collectorStatus, setCollectorStatus] = useState<
    "online" | "offline" | "checking"
  >("checking");

  // Action states
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [analysisMsg, setAnalysisMsg] = useState<string | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoMsg, setDemoMsg] = useState<string | null>(null);
  const [demoRounds, setDemoRounds] = useState(1);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoTotal, setDemoTotal] = useState(0);
  const startWorkflowsRef = useRef(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api
      .getAnalyticsSummary()
      .then((data) => {
        setSummary(data);
        setCollectorStatus("online");
      })
      .catch(() => setCollectorStatus("offline"));
  }, []);

  // Poll for demo progress
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // Resume polling if actions are already running (e.g. navigated away and back)
  useEffect(() => {
    let cancelled = false;
    api.getActionStatus().then((status) => {
      if (cancelled) return;
      if (status.analysis_running) {
        setAnalysisRunning(true);
        setAnalysisMsg("Running...");
      }
      if (status.demo_running) {
        setDemoRunning(true);
        setDemoMsg("In progress...");
        // Start polling to track progress
        api.getAnalyticsSummary().then((s) => {
          if (cancelled) return;
          setSummary(s);
          startWorkflowsRef.current = 0;
          pollRef.current = setInterval(async () => {
            try {
              const st = await api.getActionStatus();
              const fresh = await api.getAnalyticsSummary();
              setSummary(fresh);
              if (!st.demo_running) {
                stopPolling();
                setDemoRunning(false);
                setDemoMsg(`Done — ${fresh.total_workflows} workflows`);
                if (st.analysis_running) {
                  setAnalysisRunning(true);
                  setAnalysisMsg("Running...");
                }
              }
              if (!st.analysis_running && analysisRunning) {
                setAnalysisRunning(false);
                setAnalysisMsg("Complete");
              }
            } catch {
              stopPolling();
              setDemoRunning(false);
            }
          }, 2000);
        }).catch(() => {});
      }
    }).catch(() => {});
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRunAnalysis = async () => {
    setAnalysisRunning(true);
    setAnalysisMsg(null);
    try {
      const res = await api.runAnalysis();
      if (res.status === "already_running") {
        setAnalysisMsg("Already running");
        setAnalysisRunning(false);
        return;
      }
      setAnalysisMsg("Running...");
      // Poll status until done
      const poll = setInterval(async () => {
        try {
          const status = await api.getActionStatus();
          if (!status.analysis_running) {
            clearInterval(poll);
            setAnalysisRunning(false);
            setAnalysisMsg("Complete");
            // Refresh summary
            api.getAnalyticsSummary().then(setSummary).catch(() => {});
          }
        } catch {
          clearInterval(poll);
          setAnalysisRunning(false);
          setAnalysisMsg("Error checking status");
        }
      }, 3000);
    } catch (err: unknown) {
      setAnalysisRunning(false);
      setAnalysisMsg(err instanceof Error ? err.message : "Failed");
    }
  };

  const handleRunDemo = async () => {
    setDemoRunning(true);
    setDemoMsg(null);
    setDemoProgress(0);
    startWorkflowsRef.current = summary?.total_workflows ?? 0;
    try {
      const res = await api.runDemo(demoRounds);
      if (res.status === "already_running") {
        setDemoMsg("Already running");
        setDemoRunning(false);
        return;
      }
      const total = res.total_scenarios || 5;
      setDemoTotal(total);
      setDemoMsg(`0 / ${total} scenarios`);

      // Poll workflow count to track progress
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const status = await api.getActionStatus();
          const s = await api.getAnalyticsSummary();
          setSummary(s);
          const completed = Math.min(
            s.total_workflows - startWorkflowsRef.current,
            total
          );
          setDemoProgress(completed);
          setDemoMsg(`${completed} / ${total} scenarios`);

          if (!status.demo_running) {
            stopPolling();
            setDemoRunning(false);
            const final = s.total_workflows - startWorkflowsRef.current;
            setDemoMsg(`Done — ${final} scenarios completed. Running analysis...`);
            setDemoProgress(total);
            handleRunAnalysis();
          }
        } catch {
          stopPolling();
          setDemoRunning(false);
          setDemoMsg("Error checking status");
        }
      }, 2000);
    } catch (err: unknown) {
      setDemoRunning(false);
      setDemoMsg(err instanceof Error ? err.message : "Failed");
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          Settings{" "}
          <InfoTooltip text="System configuration thresholds that control when guided mode activates, how optimal paths are selected, and how bottlenecks are detected. Health checks confirm backend services are reachable." />
        </h1>
        <p className="text-sm text-muted-foreground">
          System configuration and health monitoring
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Analysis Thresholds
            </p>
            <div className="space-y-3">
              {THRESHOLDS.map((t) => (
                <div
                  key={t.label}
                  className="flex items-start justify-between border-b border-border/50 pb-3 last:border-0 last:pb-0"
                >
                  <div>
                    <p className="text-sm">{t.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {t.description}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className="ml-4 shrink-0 font-mono tabular-nums"
                  >
                    {t.value}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <Card className="border-border bg-card">
            <CardContent className="p-4">
              <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                System Health
              </p>
              <div className="space-y-3">
                <HealthIndicator
                  label="Collector API"
                  icon={Server}
                  status={collectorStatus}
                />
                <HealthIndicator
                  label="PostgreSQL + pgvector"
                  icon={Database}
                  status={collectorStatus}
                />
                <HealthIndicator
                  label="Analysis Engine"
                  icon={Activity}
                  status={collectorStatus}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardContent className="p-4">
              <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Data Summary
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">Workflows</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.total_workflows) : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Events</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.total_events) : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Top Tools</p>
                  <p className="font-mono text-lg tabular-nums">
                    {summary ? formatNumber(summary.top_tools.length) : "-"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card className="border-border bg-card">
            <CardContent className="p-4">
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Actions{" "}
                <InfoTooltip text="Run the analysis pipeline to discover optimal paths from recorded workflows, or run a demo round to generate 5 new scenario executions." />
              </p>

              <div className="flex items-center gap-3">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={analysisRunning || collectorStatus !== "online"}
                  onClick={handleRunAnalysis}
                >
                  {analysisRunning ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <FlaskConical className="h-3 w-3" />
                  )}
                  {analysisRunning ? "Running..." : "Run Analysis"}
                </Button>

                <div className="flex items-center rounded-md border border-border">
                  <div className="flex items-center gap-1.5 border-r border-border px-2.5 py-1.5">
                    <span className="text-xs text-muted-foreground">Rounds</span>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={demoRounds}
                      onChange={(e) =>
                        setDemoRounds(Math.max(1, Math.min(10, Number(e.target.value) || 1)))
                      }
                      disabled={demoRunning}
                      className="h-5 w-8 bg-transparent text-center text-sm font-mono tabular-nums text-foreground outline-none disabled:opacity-50"
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={demoRunning || collectorStatus !== "online"}
                    onClick={handleRunDemo}
                    className="rounded-l-none border-0"
                  >
                    {demoRunning ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Play className="h-3 w-3" />
                    )}
                    {demoRunning
                      ? "Running..."
                      : `Run Demo (${demoRounds * 5})`}
                  </Button>
                </div>
              </div>

              {/* Analysis feedback */}
              {analysisMsg && !demoRunning && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {analysisMsg === "Complete" ? (
                    <span className="text-emerald-400">{analysisMsg}</span>
                  ) : analysisMsg.startsWith("Error") || analysisMsg.startsWith("Failed") ? (
                    <span className="text-red-400">{analysisMsg}</span>
                  ) : (
                    analysisMsg
                  )}
                </p>
              )}

              {/* Demo progress */}
              {(demoRunning || (demoMsg && demoProgress > 0)) && (
                <div className="mt-3 space-y-1.5">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                      style={{
                        width: `${demoTotal > 0 ? (demoProgress / demoTotal) * 100 : 0}%`,
                      }}
                    />
                  </div>
                  <p className="text-xs tabular-nums text-muted-foreground">
                    {demoMsg && demoMsg.startsWith("Done") ? (
                      <span className="text-emerald-400">{demoMsg}</span>
                    ) : (
                      demoMsg
                    )}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

import type {
  AnalyticsSummary,
  BottlenecksResponse,
  ClusterDetailResponse,
  ComparisonResponse,
  ExecutionGraphResponse,
  ModeDistribution,
  OptimalPathsResponse,
  SavingsResponse,
  TaskClustersResponse,
  TimelineResponse,
  TraceOut,
  WorkflowListResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:9000";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getAnalyticsSummary: () => fetchApi<AnalyticsSummary>("/analytics/summary"),

  getWorkflows: (limit = 50, offset = 0) =>
    fetchApi<WorkflowListResponse>(`/workflows?limit=${limit}&offset=${offset}`),

  getWorkflowTrace: (workflowId: string) =>
    fetchApi<TraceOut>(`/workflows/${workflowId}/trace`),

  getOptimalPaths: () => fetchApi<OptimalPathsResponse>("/optimal-paths"),

  getModeDistribution: () =>
    fetchApi<ModeDistribution>("/analytics/mode-distribution"),

  getComparison: () => fetchApi<ComparisonResponse>("/analytics/comparison"),

  getTimeline: () => fetchApi<TimelineResponse>("/analytics/timeline"),

  getExecutionGraph: () =>
    fetchApi<ExecutionGraphResponse>("/analytics/execution-graph"),

  getBottlenecks: () => fetchApi<BottlenecksResponse>("/analytics/bottlenecks"),

  getSavings: () => fetchApi<SavingsResponse>("/analytics/savings"),

  getTaskClusters: () => fetchApi<TaskClustersResponse>("/task-clusters"),

  getClusterDetail: (pathId: string) =>
    fetchApi<ClusterDetailResponse>(`/task-clusters/${pathId}/workflows`),
};

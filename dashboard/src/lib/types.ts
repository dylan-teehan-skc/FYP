export interface AnalyticsSummary {
  total_workflows: number;
  total_events: number;
  avg_duration_ms: number | null;
  avg_steps: number | null;
  success_rate: number | null;
  top_tools: ToolStat[];
}

export interface ToolStat {
  tool_name: string;
  call_count: number;
  avg_duration_ms: number;
}

export interface WorkflowListItem {
  workflow_id: string;
  task_description: string;
  status: string;
  mode: string;
  duration_ms: number;
  steps: number;
  timestamp: string;
}

export interface WorkflowListResponse {
  workflows: WorkflowListItem[];
  total: number;
}

export interface EventOut {
  event_id: string;
  workflow_id: string;
  timestamp: string;
  activity: string;
  agent_name: string;
  agent_role: string;
  tool_name: string | null;
  tool_parameters: Record<string, unknown>;
  tool_response: Record<string, unknown>;
  llm_model: string;
  llm_prompt_tokens: number;
  llm_completion_tokens: number;
  llm_reasoning: string;
  llm_prompt: string;
  duration_ms: number;
  cost_usd: number;
  status: string;
  error_message: string | null;
  step_number: number;
  parent_event_id: string | null;
}

export interface TraceOut {
  workflow_id: string;
  task_description: string | null;
  events: EventOut[];
  total_events: number;
}

export interface OptimalPath {
  path_id: string;
  task_cluster: string;
  tool_sequence: string[];
  avg_duration_ms: number;
  avg_steps: number;
  success_rate: number;
  execution_count: number;
  updated_at: string;
}

export interface OptimalPathsResponse {
  paths: OptimalPath[];
}

export interface ModeDistribution {
  exploration: number;
  guided: number;
  total: number;
}

export interface ModeStats {
  avg_duration_ms: number;
  avg_steps: number;
  success_rate: number;
  count: number;
  avg_cost_usd?: number | null;
}

export interface ComparisonResponse {
  exploration: ModeStats;
  guided: ModeStats;
}

export interface TimelinePoint {
  date: string;
  workflows: number;
  avg_duration_ms: number;
  success_rate: number;
  guided_pct: number;
}

export interface TimelineResponse {
  points: TimelinePoint[];
}

export interface GraphNode {
  id: string;
  label: string;
  avg_duration_ms: number;
  call_count: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface ExecutionGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BottleneckTool {
  tool_name: string;
  call_count: number;
  avg_duration_ms: number;
  total_cost_usd: number;
  avg_calls_per_workflow: number;
}

export interface BottlenecksResponse {
  tools: BottleneckTool[];
}

export interface SavingsResponse {
  time_saved_ms: number;
  cost_saved_usd: number;
  pct_duration_improvement: number;
  pct_steps_improvement: number;
  pct_success_improvement: number;
  guided_count: number;
}

// === Task Cluster types ===

export interface TaskClusterSummary {
  path_id: string;
  task_cluster: string;
  tool_sequence: string[];
  avg_duration_ms: number | null;
  avg_steps: number | null;
  success_rate: number | null;
  execution_count: number;
  workflow_count: number;
  updated_at: string;
  task_description: string | null;
}

export interface TaskClustersResponse {
  clusters: TaskClusterSummary[];
}

export interface ClusterGroup {
  name: string;
  subclusters: TaskClusterSummary[];
  total_workflows: number;
}

export interface ClusterGroupsResponse {
  groups: ClusterGroup[];
}

export interface ClusterWorkflow {
  workflow_id: string;
  task_description: string | null;
  similarity: number;
  status: string;
  duration_ms: number | null;
  steps: number | null;
  mode: string;
  timestamp: string;
  cost_usd: number | null;
}

export interface ClusterModeStats {
  exploration: ModeStats;
  guided: ModeStats;
}

export interface ClusterDetailResponse {
  path_id: string;
  task_cluster: string;
  tool_sequence: string[];
  avg_duration_ms: number | null;
  avg_steps: number | null;
  success_rate: number | null;
  execution_count: number;
  updated_at: string;
  workflows: ClusterWorkflow[];
  mode_stats: ClusterModeStats;
  avg_conformance: number | null;
}

export interface DistinctPath {
  tool_sequence: string[];
  workflow_count: number;
}

export interface ClusterGroupDetailResponse {
  name: string;
  subclusters: TaskClusterSummary[];
  total_workflows: number;
  avg_duration_ms: number | null;
  avg_steps: number | null;
  success_rate: number | null;
  workflows: ClusterWorkflow[];
  mode_stats: ClusterModeStats;
  avg_conformance: number | null;
  optimal_sequence: string[];
  distinct_paths: DistinctPath[];
}

// === Action types ===

export interface ActionResponse {
  status: string;
  message: string;
  total_scenarios: number;
}

export interface ActionStatusResponse {
  demo_running: boolean;
  analysis_running: boolean;
  langchain_single_running: boolean;
  langchain_multi_running: boolean;
  message: string;
  last_error: string;
}

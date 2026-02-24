"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dagre from "dagre";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { api } from "@/lib/api";
import type { OptimalPathsResponse } from "@/lib/types";
import { ToolNode, type ToolNodeData, type ToolNodeType } from "./tool-node";
import { DetailPanel } from "./detail-panel";

// ─── dagre layout ─────────────────────────────────────────────────────────────

const NODE_WIDTH = 176;
const NODE_HEIGHT = 64;

function applyDagreLayout(
  nodes: ToolNodeType[],
  edges: Edge[]
): { nodes: ToolNodeType[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "LR",
    nodesep: 48,
    ranksep: 80,
    marginx: 24,
    marginy: 24,
  });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const positioned = nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: positioned, edges };
}

// ─── edge weight → stroke width ───────────────────────────────────────────────

function weightToStrokeWidth(weight: number, maxWeight: number): number {
  if (maxWeight === 0) return 1;
  const normalised = weight / maxWeight;
  return Math.max(1, Math.round(normalised * 5));
}

// ─── build optimal path edge set ──────────────────────────────────────────────

function buildOptimalEdgeSet(paths: OptimalPathsResponse): Set<string> {
  const set = new Set<string>();
  for (const path of paths.paths) {
    const seq = path.tool_sequence;
    for (let i = 0; i < seq.length - 1; i++) {
      set.add(`${seq[i]}->${seq[i + 1]}`);
    }
  }
  return set;
}

// ─── node type registry ───────────────────────────────────────────────────────

const nodeTypes = { tool: ToolNode };

// ─── component ────────────────────────────────────────────────────────────────

export function ExecutionDag() {
  const [nodes, setNodes, onNodesChange] = useNodesState<ToolNodeType>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeData, setSelectedNodeData] = useState<ToolNodeData | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const [graphData, pathsData] = await Promise.all([
          api.getExecutionGraph(),
          api.getOptimalPaths().catch(
            (): OptimalPathsResponse => ({ paths: [] })
          ),
        ]);

        if (cancelled) return;

        const optimalEdges = buildOptimalEdgeSet(pathsData);
        const optimalNodeIds = new Set<string>();
        for (const path of pathsData.paths) {
          for (const tool of path.tool_sequence) {
            optimalNodeIds.add(tool);
          }
        }

        const maxWeight = Math.max(
          ...graphData.edges.map((e) => e.weight),
          1
        );

        const rawNodes: ToolNodeType[] = graphData.nodes.map((n) => ({
          id: n.id,
          type: "tool" as const,
          position: { x: 0, y: 0 },
          data: {
            label: n.label,
            call_count: n.call_count,
            avg_duration_ms: n.avg_duration_ms,
            isOptimal: optimalNodeIds.has(n.id),
          },
        }));

        const rawEdges: Edge[] = graphData.edges.map((e) => {
          const key = `${e.source}->${e.target}`;
          const isOptimal = optimalEdges.has(key);
          const strokeWidth = weightToStrokeWidth(e.weight, maxWeight);

          return {
            id: `${e.source}__${e.target}`,
            source: e.source,
            target: e.target,
            type: "default",
            animated: isOptimal,
            style: {
              strokeWidth,
              stroke: isOptimal ? "#10b981" : "#52525b",
              filter: isOptimal
                ? "drop-shadow(0 0 3px rgba(16,185,129,0.5))"
                : undefined,
            },
            label: e.weight > 1 ? String(e.weight) : undefined,
            labelStyle: {
              fill: "#a1a1aa",
              fontSize: 9,
              fontFamily: "var(--font-mono)",
            },
            labelBgStyle: {
              fill: "#27272a",
              fillOpacity: 0.85,
            },
          };
        });

        const { nodes: laidOutNodes, edges: laidOutEdges } = applyDagreLayout(
          rawNodes,
          rawEdges
        );

        setNodes(laidOutNodes);
        setEdges(laidOutEdges);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load graph");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: ToolNodeType) => {
      setSelectedNodeData(node.data as ToolNodeData);
    },
    []
  );

  const onPaneClick = useCallback(() => {
    setSelectedNodeData(null);
  }, []);

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-600 border-t-emerald-500" />
          <p className="text-xs text-zinc-500">Loading execution graph…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-zinc-500">
          No execution data yet. Run some workflows to populate the graph.
        </p>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={proOptions}
        className="bg-zinc-900"
        defaultEdgeOptions={{ type: "default" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#3f3f46"
        />
        <Controls
          className="[&>button]:border-zinc-700 [&>button]:bg-zinc-800 [&>button]:text-zinc-300 [&>button:hover]:bg-zinc-700"
          showInteractive={false}
        />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as ToolNodeData;
            if (data.avg_duration_ms < 500) return "#10b981";
            if (data.avg_duration_ms < 2000) return "#f59e0b";
            return "#ef4444";
          }}
          maskColor="rgba(9,9,11,0.75)"
          className="border border-zinc-700 bg-zinc-800"
        />
      </ReactFlow>

      <DetailPanel
        node={selectedNodeData}
        onClose={() => setSelectedNodeData(null)}
      />
    </div>
  );
}

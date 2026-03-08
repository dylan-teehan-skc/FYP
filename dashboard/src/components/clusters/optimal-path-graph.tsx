"use client";

import React, { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { ToolNode, type ToolNodeData, type ToolNodeType } from "../graph/tool-node";
import { DetailPanel } from "../graph/detail-panel";
import { NODE_WIDTH, NODE_HEIGHT } from "../graph/layout-utils";

interface OptimalPathGraphProps {
  optimalSequence: string[];
}

const nodeTypes = { tool: ToolNode };

const H_GAP = 60;

export function OptimalPathGraph({ optimalSequence }: OptimalPathGraphProps) {
  const [selectedNodeData, setSelectedNodeData] = useState<ToolNodeData | null>(
    null,
  );

  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: ToolNodeType[] = optimalSequence.map((tool, i) => ({
      id: `${tool}_${i}`,
      type: "tool" as const,
      position: {
        x: i * (NODE_WIDTH + H_GAP),
        y: 0,
      },
      data: {
        label: tool,
        call_count: i + 1,
        avg_duration_ms: 0,
        isOptimal: true,
      },
    }));

    const edges: Edge[] = [];
    for (let i = 0; i < optimalSequence.length - 1; i++) {
      const sourceId = `${optimalSequence[i]}_${i}`;
      const targetId = `${optimalSequence[i + 1]}_${i + 1}`;
      edges.push({
        id: `${sourceId}__${targetId}`,
        source: sourceId,
        target: targetId,
        type: "default",
        animated: true,
        style: {
          strokeWidth: 3,
          stroke: "#10b981",
          filter: "drop-shadow(0 0 3px rgba(16,185,129,0.5))",
        },
      });
    }

    return { initialNodes: nodes, initialEdges: edges };
  }, [optimalSequence]);

  const [nodes, , onNodesChange] = useNodesState<ToolNodeType>(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState<Edge>(initialEdges);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: ToolNodeType) => {
      setSelectedNodeData(node.data as ToolNodeData);
    },
    [],
  );

  const onPaneClick = useCallback(() => {
    setSelectedNodeData(null);
  }, []);

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  if (optimalSequence.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-zinc-500">No optimal path available.</p>
      </div>
    );
  }

  return (
    <div className="relative w-full" style={{ height: NODE_HEIGHT * 3 + 40 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={proOptions}
        className="rounded-md bg-zinc-900"
        defaultEdgeOptions={{ type: "default" }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
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
      </ReactFlow>

      <DetailPanel
        node={selectedNodeData}
        onClose={() => setSelectedNodeData(null)}
      />
    </div>
  );
}

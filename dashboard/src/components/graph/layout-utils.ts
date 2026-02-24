import dagre from "dagre";
import type { Edge } from "@xyflow/react";
import type { ToolNodeType } from "./tool-node";

export const NODE_WIDTH = 176;
export const NODE_HEIGHT = 64;

export function applyDagreLayout(
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
    if (edge.source !== edge.target) {
      g.setEdge(edge.source, edge.target);
    }
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

export function weightToStrokeWidth(weight: number, maxWeight: number): number {
  if (maxWeight === 0) return 1;
  const normalised = weight / maxWeight;
  return Math.max(1, Math.round(normalised * 5));
}

export function buildOptimalEdgeSet(
  toolSequences: string[][]
): Set<string> {
  const set = new Set<string>();
  for (const seq of toolSequences) {
    for (let i = 0; i < seq.length - 1; i++) {
      set.add(`${seq[i]}->${seq[i + 1]}`);
    }
  }
  return set;
}

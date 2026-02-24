import type { OptimalPath } from "./types";

export type StepAlignment = {
  toolName: string;
  status: "match" | "deviation" | "extra";
};

export interface PathMatch {
  path: OptimalPath;
  score: number;
  alignment: StepAlignment[];
}

export function findBestMatch(
  toolSequence: string[],
  paths: OptimalPath[],
): PathMatch | null {
  if (paths.length === 0 || toolSequence.length === 0) return null;

  let bestPath: OptimalPath | null = null;
  let bestScore = -1;

  for (const path of paths) {
    const pathSeq = path.tool_sequence;
    let matches = 0;
    const minLen = Math.min(toolSequence.length, pathSeq.length);
    for (let i = 0; i < minLen; i++) {
      if (toolSequence[i] === pathSeq[i]) matches++;
    }
    const score = minLen > 0 ? matches / minLen : 0;
    if (score > bestScore) {
      bestScore = score;
      bestPath = path;
    }
  }

  if (!bestPath) return null;

  return {
    path: bestPath,
    score: bestScore,
    alignment: buildAlignment(toolSequence, bestPath.tool_sequence),
  };
}

export function buildAlignment(
  toolSequence: string[],
  optimalSequence: string[],
): StepAlignment[] {
  return toolSequence.map((toolName, index) => {
    if (index >= optimalSequence.length) {
      return { toolName, status: "extra" };
    }
    return {
      toolName,
      status: toolName === optimalSequence[index] ? "match" : "deviation",
    };
  });
}

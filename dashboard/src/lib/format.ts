export function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCost(usd: number | null): string {
  if (usd === null || usd === undefined) return "-";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export function formatNumber(n: number | null): string {
  if (n === null || n === undefined) return "-";
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toFixed(1);
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDelta(before: number, after: number): {
  label: string;
  pct: number;
  improved: boolean;
} {
  if (before === 0) return { label: "-", pct: 0, improved: false };
  const pct = ((before - after) / before) * 100;
  const improved = pct > 0;
  const arrow = improved ? "\u2193" : "\u2191";
  return {
    label: `${arrow}${Math.abs(pct).toFixed(0)}%`,
    pct,
    improved,
  };
}

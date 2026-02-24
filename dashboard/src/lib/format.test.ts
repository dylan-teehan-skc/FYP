import { describe, it, expect } from "vitest";
import { formatCost, formatDelta, formatDuration, formatNumber } from "./format";

describe("formatCost", () => {
  it("formats small costs with 4 decimal places", () => {
    expect(formatCost(0.0023)).toBe("$0.0023");
  });

  it("formats normal costs with 2 decimal places", () => {
    expect(formatCost(0.85)).toBe("$0.85");
    expect(formatCost(1.5)).toBe("$1.50");
  });

  it("returns dash for null", () => {
    expect(formatCost(null)).toBe("-");
  });

  it("handles zero", () => {
    expect(formatCost(0)).toBe("$0.0000");
  });
});

describe("formatDelta", () => {
  it("computes improvement when value decreases", () => {
    const result = formatDelta(10, 5);
    expect(result.pct).toBe(50);
    expect(result.improved).toBe(true);
    expect(result.label).toContain("50%");
  });

  it("computes regression when value increases", () => {
    const result = formatDelta(5, 10);
    expect(result.pct).toBe(-100);
    expect(result.improved).toBe(false);
    expect(result.label).toContain("100%");
  });

  it("returns dash when before is zero", () => {
    const result = formatDelta(0, 5);
    expect(result.label).toBe("-");
    expect(result.pct).toBe(0);
  });

  it("handles equal values", () => {
    const result = formatDelta(5, 5);
    expect(result.pct).toBe(0);
    expect(result.label).toContain("0%");
  });
});

describe("formatDuration", () => {
  it("formats ms under 1000", () => {
    expect(formatDuration(450)).toBe("450ms");
  });

  it("formats seconds", () => {
    expect(formatDuration(2500)).toBe("2.5s");
  });

  it("returns dash for null", () => {
    expect(formatDuration(null)).toBe("-");
  });
});

describe("formatNumber", () => {
  it("formats integers", () => {
    expect(formatNumber(42)).toBe("42");
  });

  it("formats decimals to 1 place", () => {
    expect(formatNumber(3.14159)).toBe("3.1");
  });

  it("returns dash for null", () => {
    expect(formatNumber(null)).toBe("-");
  });
});

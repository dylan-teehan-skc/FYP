import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CostLeakList } from "./cost-leak-list";
import type { BottleneckTool } from "@/lib/types";

const sampleTools: BottleneckTool[] = [
  {
    tool_name: "search_knowledge_base",
    call_count: 42,
    avg_duration_ms: 1200,
    total_cost_usd: 0.85,
    avg_calls_per_workflow: 3.5,
  },
  {
    tool_name: "get_order_details",
    call_count: 20,
    avg_duration_ms: 800,
    total_cost_usd: 0.32,
    avg_calls_per_workflow: 1.2,
  },
  {
    tool_name: "check_ticket_status",
    call_count: 15,
    avg_duration_ms: 450,
    total_cost_usd: 0.12,
    avg_calls_per_workflow: 1.0,
  },
];

describe("CostLeakList", () => {
  it("renders tool names sorted by cost descending", () => {
    render(<CostLeakList tools={sampleTools} />);
    const toolNames = screen.getAllByText(
      /search_knowledge_base|get_order_details|check_ticket_status/
    );
    expect(toolNames[0]).toHaveTextContent("search_knowledge_base");
    expect(toolNames[1]).toHaveTextContent("get_order_details");
    expect(toolNames[2]).toHaveTextContent("check_ticket_status");
  });

  it("shows redundancy badge for tools called >2x per workflow", () => {
    render(<CostLeakList tools={sampleTools} />);
    const badges = screen.getAllByText("redundant");
    expect(badges).toHaveLength(1);
  });

  it("displays formatted cost values", () => {
    render(<CostLeakList tools={sampleTools} />);
    expect(screen.getByText("$0.85")).toBeInTheDocument();
    expect(screen.getByText("$0.32")).toBeInTheDocument();
    expect(screen.getByText("$0.12")).toBeInTheDocument();
  });

  it("displays avg calls per workflow", () => {
    render(<CostLeakList tools={sampleTools} />);
    expect(screen.getByText("3.5×")).toBeInTheDocument();
    expect(screen.getByText("1.2×")).toBeInTheDocument();
    expect(screen.getByText("1.0×")).toBeInTheDocument();
  });

  it("shows empty state when no tools", () => {
    render(<CostLeakList tools={[]} />);
    expect(screen.getByText("No tool data available")).toBeInTheDocument();
  });

  it("shows redundancy warning text for redundant tools", () => {
    render(<CostLeakList tools={sampleTools} />);
    expect(
      screen.getByText(/3\.5× per workflow on average/)
    ).toBeInTheDocument();
  });
});

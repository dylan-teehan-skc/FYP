import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DeltaCard } from "./delta-card";

describe("DeltaCard", () => {
  it("renders cost comparison with cents unit", () => {
    render(
      <DeltaCard
        label="Avg Cost"
        before={4.5}
        after={2.1}
        unit="¢"
        lowerIsBetter={true}
      />
    );
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
    expect(screen.getByText("4.5")).toBeInTheDocument();
    expect(screen.getByText("2.1")).toBeInTheDocument();
    expect(screen.getAllByText("¢")).toHaveLength(2);
  });

  it("shows green improvement when cost decreases (lowerIsBetter)", () => {
    const { container } = render(
      <DeltaCard
        label="Avg Cost"
        before={10}
        after={5}
        unit="¢"
        lowerIsBetter={true}
      />
    );
    const badge = container.querySelector("[class*='emerald']");
    expect(badge).toBeTruthy();
  });

  it("shows red regression when cost increases (lowerIsBetter)", () => {
    const { container } = render(
      <DeltaCard
        label="Avg Cost"
        before={5}
        after={10}
        unit="¢"
        lowerIsBetter={true}
      />
    );
    const badge = container.querySelector("[class*='red']");
    expect(badge).toBeTruthy();
  });

  it("renders API calls comparison", () => {
    render(
      <DeltaCard
        label="API Calls"
        before={8.5}
        after={5.2}
        unit="calls"
        lowerIsBetter={true}
      />
    );
    expect(screen.getByText("API Calls")).toBeInTheDocument();
    expect(screen.getByText("8.5")).toBeInTheDocument();
    expect(screen.getByText("5.2")).toBeInTheDocument();
  });

  it("handles zero before value without crashing", () => {
    render(
      <DeltaCard
        label="Avg Cost"
        before={0}
        after={0}
        unit="¢"
        lowerIsBetter={true}
      />
    );
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
  });
});

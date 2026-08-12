import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionForm } from "./decision-form";

describe("DecisionForm", () => {
  it("offers desk rejection only from under_screening", () => {
    render(<DecisionForm trackingCode="UGJCS-2026-0001" status="under_screening" onDecided={vi.fn()} />);
    expect(screen.getByRole("option", { name: /desk reject/i })).toBeInTheDocument();
  });

  it("renders nothing once the manuscript has reached a state with no legal decision", () => {
    const { container } = render(<DecisionForm trackingCode="UGJCS-2026-0001" status="published" onDecided={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

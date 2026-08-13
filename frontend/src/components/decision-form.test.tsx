import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionForm } from "./decision-form";

describe("DecisionForm", () => {
  it("offers desk rejection only from under_screening", () => {
    render(<DecisionForm trackingCode="SDJ-2026-0001" status="under_screening" onDecided={vi.fn()} />);
    expect(screen.getByRole("option", { name: /desk reject/i })).toBeInTheDocument();
  });

  it("renders nothing once the manuscript has reached a state with no legal decision", () => {
    const { container } = render(<DecisionForm trackingCode="SDJ-2026-0001" status="published" onDecided={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("replaces every underscore in a label, not just the first", () => {
    // `send_to_review` has two underscores — the exact case a single non-global
    // `.replace("_", " ")` mangles into "send to_review".
    render(<DecisionForm trackingCode="SDJ-2026-0001" status="under_screening" onDecided={vi.fn()} />);
    expect(screen.getByRole("option", { name: "send to review" })).toBeInTheDocument();
    expect(screen.queryByText("send to_review")).not.toBeInTheDocument();
  });

  it("offers sending a resubmission straight back to review", () => {
    render(<DecisionForm trackingCode="SDJ-2026-0001" status="resubmitted" onDecided={vi.fn()} />);
    expect(screen.getByRole("option", { name: "send to review" })).toBeInTheDocument();
  });
});

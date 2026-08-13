import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge, StatusExplanation } from "./badge";

describe("StatusBadge", () => {
  it("renders a human label for every manuscript status", () => {
    render(<StatusBadge status="under_screening" />);
    expect(screen.getByText("Under screening")).toBeInTheDocument();
  });

  it("distinguishes rejection tones from acceptance tones", () => {
    const { rerender } = render(<StatusBadge status="rejected" />);
    expect(screen.getByText("Rejected")).toHaveClass("text-seal");
    rerender(<StatusBadge status="accepted" />);
    expect(screen.getByText("Accepted")).toHaveClass("text-verified");
  });
});

describe("StatusExplanation", () => {
  it("explains a status in words rather than naming it again", () => {
    render(<StatusExplanation status="revision_requested" />);
    expect(screen.getByText(/asked for changes/i)).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
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

  describe("arm-then-confirm for final decisions", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("does not record an accept on the first click — it arms and asks for confirmation", async () => {
      const fetchSpy = vi.fn();
      vi.stubGlobal("fetch", fetchSpy);
      const user = userEvent.setup();
      render(<DecisionForm trackingCode="SDJ-2026-0001" status="reviews_complete" onDecided={vi.fn()} />);

      await user.selectOptions(screen.getByLabelText("Decision"), "accept");
      await user.type(screen.getByLabelText("Rationale"), "Both reviewers recommend acceptance without reservation.");
      await user.click(screen.getByRole("button", { name: "Record decision" }));

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Confirm accept" })).toBeInTheDocument();
      // The confirm click is what records it.
      fetchSpy.mockResolvedValue({ ok: true });
      await user.click(screen.getByRole("button", { name: "Confirm accept" }));
      expect(fetchSpy).toHaveBeenCalledOnce();
    });

    it("lets 'Go back' disarm instead of recording", async () => {
      const fetchSpy = vi.fn();
      vi.stubGlobal("fetch", fetchSpy);
      const user = userEvent.setup();
      render(<DecisionForm trackingCode="SDJ-2026-0001" status="under_screening" onDecided={vi.fn()} />);

      await user.type(screen.getByLabelText("Rationale"), "Out of scope for the journal, rejecting at the desk.");
      await user.click(screen.getByRole("button", { name: "Record decision" }));
      await user.click(screen.getByRole("button", { name: "Go back" }));

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Record decision" })).toBeInTheDocument();
    });

    it("records a routine send_to_review in a single click", async () => {
      const fetchSpy = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal("fetch", fetchSpy);
      const user = userEvent.setup();
      render(<DecisionForm trackingCode="SDJ-2026-0001" status="under_screening" onDecided={vi.fn()} />);

      await user.selectOptions(screen.getByLabelText("Decision"), "send_to_review");
      await user.type(screen.getByLabelText("Rationale"), "Well within scope; sending out to two reviewers now.");
      await user.click(screen.getByRole("button", { name: "Record decision" }));

      expect(fetchSpy).toHaveBeenCalledOnce();
    });
  });
});

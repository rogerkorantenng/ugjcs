import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProvenancePanel } from "./provenance-panel";
import type { ProvenanceOut } from "@/types/scholarly";

const HEAD_HASH = "0123456789abcdef".repeat(4); // 64 hex chars, like a real digest

function provenance(intact: boolean): ProvenanceOut {
  return {
    tracking_code: "SDJ-2026-0004",
    intact,
    head_hash: HEAD_HASH,
    events: [
      { sequence: 1, event_type: "submission_received", occurred_at: "2026-01-10T09:00:00Z", hash_prefix: "a1b2c3d4" },
      { sequence: 2, event_type: "sent_to_review", occurred_at: "2026-01-12T14:30:00Z", hash_prefix: "e5f6a7b8" },
    ],
  };
}

function stubFetch(body: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 404, json: async () => body }));
}

describe("ProvenancePanel", () => {
  it("verifies an intact chain: verdict in verified green, truncated head hash, events in words", async () => {
    stubFetch(provenance(true));
    render(<ProvenancePanel trackingCode="SDJ-2026-0004" />);

    await userEvent.click(screen.getByRole("button", { name: /verify chain/i }));

    const verdict = await screen.findByText("Chain intact ✓");
    expect(verdict).toHaveClass("text-verified");
    // Truncated in the middle, full digest preserved in the title attribute.
    expect(screen.getByTitle(HEAD_HASH)).toHaveTextContent("0123456789…89abcdef");
    // Event types read as words — underscores gone, every one of them.
    expect(screen.getByText("submission received")).toBeInTheDocument();
    expect(screen.getByText("sent to review")).toBeInTheDocument();
    expect(screen.queryByText("sent_to_review")).not.toBeInTheDocument();
    expect(screen.getByText(/cannot prove events were never removed from the tail/i)).toBeInTheDocument();
  });

  it("shows CHAIN BROKEN in seal red when the backend reports intact: false", async () => {
    stubFetch(provenance(false));
    render(<ProvenancePanel trackingCode="SDJ-2026-0004" />);

    await userEvent.click(screen.getByRole("button", { name: /verify chain/i }));

    const verdict = await screen.findByText("CHAIN BROKEN");
    expect(verdict).toHaveClass("text-seal");
    expect(screen.queryByText("Chain intact ✓")).not.toBeInTheDocument();
    // The honest caveat still shows — a broken verdict is a verification result too.
    expect(screen.getByText(/cannot prove events were never removed from the tail/i)).toBeInTheDocument();
  });

  it("relays a problem title as an error panel with a retry, not a blank screen", async () => {
    stubFetch({ type: "about:blank", title: "Paper not found", status: 404 }, false);
    render(<ProvenancePanel trackingCode="SDJ-2026-9999" />);

    await userEvent.click(screen.getByRole("button", { name: /verify chain/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Paper not found"));
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});

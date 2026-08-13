import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReviewerPicker } from "./reviewer-picker";
import type { ReviewerCandidate } from "@/types/api";

const CANDIDATES: ReviewerCandidate[] = [
  { id: "r-1", full_name: "Dr. Ama Owusu", affiliation: "University of Ghana", active_assignments: 1, reviewer_capacity: 3, excluded_reason: null },
  {
    id: "r-2",
    full_name: "Dr. Kojo Mensah",
    affiliation: "University of Ghana",
    active_assignments: 0,
    reviewer_capacity: 3,
    excluded_reason: "shares an affiliation with an author",
  },
];

function mockFetch() {
  return vi.fn((url: string, init?: RequestInit) => {
    if (!init || init.method === undefined) {
      return Promise.resolve({ ok: true, status: 200, json: async () => CANDIDATES });
    }
    return Promise.resolve({ ok: true, status: 204, json: async () => null });
  }) as unknown as typeof fetch;
}

describe("ReviewerPicker", () => {
  it("shows an excluded candidate greyed out with its reason visible, not hidden", async () => {
    vi.stubGlobal("fetch", mockFetch());
    render(<ReviewerPicker trackingCode="UGJCS-2026-0001" onAssigned={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Dr. Kojo Mensah")).toBeInTheDocument());
    expect(screen.getByText(/shares an affiliation with an author/i)).toBeInTheDocument();
    const radios = screen.getAllByRole("radio");
    expect(radios[1]).toBeDisabled();
  });

  it("posts the selected candidate's id, not a typed id", async () => {
    const fetchSpy = mockFetch();
    vi.stubGlobal("fetch", fetchSpy);
    render(<ReviewerPicker trackingCode="UGJCS-2026-0001" onAssigned={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Dr. Ama Owusu")).toBeInTheDocument());
    const radios = screen.getAllByRole("radio");
    await userEvent.click(radios[0]);
    await userEvent.click(screen.getByRole("button", { name: /assign selected reviewer/i }));

    await waitFor(() => {
      const postCall = (fetchSpy as unknown as { mock: { calls: [string, RequestInit][] } }).mock.calls.find(
        ([, init]) => init?.method === "POST",
      );
      expect(postCall).toBeDefined();
      expect(JSON.parse(postCall![1].body as string)).toEqual({ reviewer_id: "r-1" });
    });
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReviewerAssignForm } from "./reviewer-assign-form";

describe("ReviewerAssignForm", () => {
  it("posts the entered reviewer id to the editorial reviewers endpoint", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    vi.stubGlobal("fetch", fetchSpy);

    render(<ReviewerAssignForm trackingCode="UGJCS-2026-0001" onAssigned={vi.fn()} />);
    const { default: userEvent } = await import("@testing-library/user-event");
    await userEvent.type(screen.getByLabelText(/reviewer account id/i), "r-1234");
    await userEvent.click(screen.getByRole("button", { name: /^assign$/i }));

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/editorial/UGJCS-2026-0001/reviewers",
      expect.objectContaining({ method: "POST" }),
    );
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ reviewer_id: "r-1234" });
  });
});

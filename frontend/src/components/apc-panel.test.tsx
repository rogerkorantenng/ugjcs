import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApcPanel } from "./apc-panel";
import type { BillingInvoice } from "@/types/wave2";

// SWR's module-level cache persists across tests, so every test uses its own tracking
// code — a stale cached invoice can never leak into the next assertion.
function invoice(overrides: Partial<BillingInvoice> = {}): BillingInvoice {
  return { amount_pesewas: 15000, status: "pending", paystack_reference: null, settled_at: null, ...overrides };
}

function stubFetch(handler: (url: string, init?: RequestInit) => { status: number; body: unknown }) {
  const spy = vi.fn((url: string, init?: RequestInit) => {
    const { status, body } = handler(url, init);
    return Promise.resolve({ ok: status < 400, status, json: async () => body });
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

describe("ApcPanel", () => {
  it("renders a pending invoice with the amount in cedis and a Paystack button", async () => {
    stubFetch(() => ({ status: 200, body: invoice() }));
    render(<ApcPanel trackingCode="SDJ-2026-1001" variant="author" />);

    expect(await screen.findByText("GHS 150.00")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pay with paystack/i })).toBeInTheDocument();
  });

  it("renders a paid invoice with its Paystack reference and no pay button", async () => {
    stubFetch(() => ({
      status: 200,
      body: invoice({ status: "paid", paystack_reference: "PS-REF-42", settled_at: "2026-08-01T09:00:00Z" }),
    }));
    render(<ApcPanel trackingCode="SDJ-2026-1002" variant="author" />);

    expect(await screen.findByText("paid")).toBeInTheDocument();
    expect(screen.getByText(/PS-REF-42/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pay with paystack/i })).not.toBeInTheDocument();
  });

  it("renders a waived invoice as settled by the Editor-in-Chief, with no pay button", async () => {
    stubFetch(() => ({ status: 200, body: invoice({ status: "waived" }) }));
    render(<ApcPanel trackingCode="SDJ-2026-1003" variant="author" />);

    expect(await screen.findByText("waived")).toBeInTheDocument();
    expect(screen.getByText(/waived this charge — nothing is owed/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pay with paystack/i })).not.toBeInTheDocument();
  });

  it("treats {mock: true} from initialize as already paid: shows the note and refetches", async () => {
    let settled = false;
    const fetchSpy = stubFetch((url, init) => {
      if (init?.method === "POST") {
        settled = true;
        return { status: 200, body: { mock: true } };
      }
      return { status: 200, body: settled ? invoice({ status: "paid" }) : invoice() };
    });
    render(<ApcPanel trackingCode="SDJ-2026-1004" variant="author" />);

    await userEvent.click(await screen.findByRole("button", { name: /pay with paystack/i }));

    expect(await screen.findByText("Paid (mock gateway)")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("paid")).toBeInTheDocument());
    const getCalls = fetchSpy.mock.calls.filter(([, init]) => init?.method === undefined);
    expect(getCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("renders a 404 as 'no invoice raised yet', not as an error", async () => {
    stubFetch(() => ({ status: 404, body: { type: "about:blank", title: "No invoice", status: 404 } }));
    render(<ApcPanel trackingCode="SDJ-2026-1005" variant="author" />);

    expect(await screen.findByText(/no processing charge has been raised/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("lets an Editor-in-Chief waive only after an explicit confirmation step", async () => {
    const fetchSpy = stubFetch((url, init) => {
      if (init?.method === "POST") return { status: 200, body: invoice({ status: "waived" }) };
      return { status: 200, body: invoice() };
    });
    render(<ApcPanel trackingCode="SDJ-2026-1006" variant="editor" canWaive />);

    await userEvent.click(await screen.findByRole("button", { name: /waive charge/i }));
    expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);

    await userEvent.click(screen.getByRole("button", { name: /confirm waiver/i }));
    await waitFor(() => {
      const post = fetchSpy.mock.calls.find(([, init]) => init?.method === "POST");
      expect(post?.[0]).toBe("/api/billing/SDJ-2026-1006/waive");
    });
  });

  it("never offers the waive control to a plain editor", async () => {
    stubFetch(() => ({ status: 200, body: invoice() }));
    render(<ApcPanel trackingCode="SDJ-2026-1007" variant="editor" canWaive={false} />);

    expect(await screen.findByText("GHS 150.00")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /waive charge/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pay with paystack/i })).not.toBeInTheDocument();
  });
});

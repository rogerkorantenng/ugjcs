import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AccountsTable } from "./accounts-table";
import type { AdminAccount } from "@/types/wave2";

const AUTHOR: AdminAccount = {
  id: "acc-1",
  email: "ama@ug.edu.gh",
  full_name: "Dr. Ama Owusu",
  affiliation: "University of Ghana",
  roles: ["author"],
  reviewer_capacity: 3,
  is_active: true,
  is_verified: true,
};

const REVIEWER: AdminAccount = {
  ...AUTHOR,
  id: "acc-2",
  email: "kojo@ug.edu.gh",
  full_name: "Dr. Kojo Mensah",
  roles: ["author", "reviewer"],
};

function stubFetch() {
  const spy = vi.fn(() => Promise.resolve({ ok: true, status: 200, json: async () => ({}) }));
  vi.stubGlobal("fetch", spy);
  return spy as unknown as { mock: { calls: [string, RequestInit][] } };
}

function postCalls(spy: { mock: { calls: [string, RequestInit][] } }) {
  return spy.mock.calls.filter(([, init]) => init?.method === "POST");
}

describe("AccountsTable", () => {
  it("renders each account with its roles as chips", () => {
    stubFetch();
    render(<AccountsTable accounts={[AUTHOR, REVIEWER]} onChanged={vi.fn()} />);

    expect(screen.getByText("ama@ug.edu.gh")).toBeInTheDocument();
    expect(screen.getByText("Dr. Kojo Mensah")).toBeInTheDocument();
    expect(screen.getAllByText("author")).toHaveLength(2);
    expect(screen.getByText("reviewer")).toBeInTheDocument();
  });

  it("posts the new reviewer capacity when the stepper changes", async () => {
    const spy = stubFetch();
    const onChanged = vi.fn();
    render(<AccountsTable accounts={[REVIEWER]} onChanged={onChanged} />);

    await userEvent.selectOptions(screen.getByLabelText(/reviewer capacity for kojo@ug.edu.gh/i), "5");

    await waitFor(() => {
      const [url, init] = postCalls(spy)[0];
      expect(url).toBe("/api/admin/accounts/acc-2/capacity");
      expect(JSON.parse(init.body as string)).toEqual({ reviewer_capacity: 5 });
    });
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("grants the reviewer role to an account that lacks it", async () => {
    const spy = stubFetch();
    render(<AccountsTable accounts={[AUTHOR]} onChanged={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /grant reviewer/i }));

    await waitFor(() => {
      const [url, init] = postCalls(spy)[0];
      expect(url).toBe("/api/admin/accounts/acc-1/roles");
      expect(JSON.parse(init.body as string)).toEqual({ role: "reviewer", grant: true });
    });
  });

  it("revokes the reviewer role from an account that holds it", async () => {
    const spy = stubFetch();
    render(<AccountsTable accounts={[REVIEWER]} onChanged={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /revoke reviewer/i }));

    await waitFor(() => {
      const [url, init] = postCalls(spy)[0];
      expect(url).toBe("/api/admin/accounts/acc-2/roles");
      expect(JSON.parse(init.body as string)).toEqual({ role: "reviewer", grant: false });
    });
  });

  it("never deactivates on the first click — a confirmation step stands in between", async () => {
    const spy = stubFetch();
    render(<AccountsTable accounts={[AUTHOR]} onChanged={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Deactivate" }));
    expect(postCalls(spy)).toHaveLength(0);

    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => {
      const [url, init] = postCalls(spy)[0];
      expect(url).toBe("/api/admin/accounts/acc-1/active");
      expect(JSON.parse(init.body as string)).toEqual({ is_active: false });
    });
  });

  it("reactivates a deactivated account with a single click", async () => {
    const spy = stubFetch();
    render(<AccountsTable accounts={[{ ...AUTHOR, is_active: false }]} onChanged={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /reactivate/i }));

    await waitFor(() => {
      const [url, init] = postCalls(spy)[0];
      expect(url).toBe("/api/admin/accounts/acc-1/active");
      expect(JSON.parse(init.body as string)).toEqual({ is_active: true });
    });
  });
});

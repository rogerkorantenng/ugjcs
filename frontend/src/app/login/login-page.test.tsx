import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => vi.restoreAllMocks());

describe("LoginPage", () => {
  it("shows the problem detail returned by the login route on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({
          type: "about:blank",
          title: "Invalid email or password",
          status: 401,
        }),
      }),
    );
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "author@ug.edu.gh");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password"));
  });

  it("is fully keyboard-operable: Tab reaches email, password, then the submit button in order", async () => {
    // The page probes `/api/auth/me` on mount; answer "signed out" so it stays put.
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ user: null }) }));
    render(<LoginPage />);
    // The masthead's home link is the page's first focusable element, ahead of the form —
    // the same order a sighted user's eye meets them in, top to bottom.
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "SDJ" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /sign in/i })).toHaveFocus();
  });
});

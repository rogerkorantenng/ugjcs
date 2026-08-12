import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
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
    vi.stubGlobal("fetch", vi.fn());
    render(<LoginPage />);
    await userEvent.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /sign in/i })).toHaveFocus();
  });
});

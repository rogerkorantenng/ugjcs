import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const signedOut = () =>
  vi.fn().mockResolvedValue({ ok: true, json: async () => ({ user: null }) });

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
    await userEvent.type(screen.getByLabelText("Email"), "author@sdj.test");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password"));
  });

  it("is fully keyboard-operable: Tab reaches the links, then email, password, submit in order", async () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    // The image half carries no focusable elements, so keyboard users land on the
    // wordmark, the way back, and then the form — top to bottom of the right panel.
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "SDJ" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /back to the journal/i })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toHaveFocus();
  });

  it("switches to a sign-up form with name and affiliation, and back again", async () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    expect(screen.queryByLabelText("Full name")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /sign up as an author/i }));
    expect(screen.getByRole("heading", { name: /create your author account/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Full name")).toBeInTheDocument();
    expect(screen.getByLabelText("Affiliation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    expect(screen.getByRole("heading", { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Full name")).not.toBeInTheDocument();
  });

  it("registers through the register route and includes every sign-up field", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/auth/me"
          ? { ok: true, json: async () => ({ user: null }) }
          : {
              ok: true,
              json: async () => ({ user: { id: "u1", email: "efua@ug.edu.gh", roles: ["author"] } }),
            },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: /sign up as an author/i }));
    await userEvent.type(screen.getByLabelText("Full name"), "Efua Sutherland");
    await userEvent.type(screen.getByLabelText("Affiliation"), "University of Ghana");
    await userEvent.type(screen.getByLabelText("Email"), "efua@ug.edu.gh");
    await userEvent.type(screen.getByLabelText("Password"), "a passphrase well over twelve");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === "/api/auth/register");
      expect(call).toBeDefined();
      const body = JSON.parse((call![1] as RequestInit).body as string);
      expect(body).toEqual({
        email: "efua@ug.edu.gh",
        password: "a passphrase well over twelve",
        full_name: "Efua Sutherland",
        affiliation: "University of Ghana",
      });
    });
  });
});

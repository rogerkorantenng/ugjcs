import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DEMO_ACCOUNTS } from "@/lib/demo-accounts";
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

  it("is fully keyboard-operable: Tab reaches the links, the demo chips, then email, password, submit in order", async () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    // The image half carries no focusable elements, so keyboard users land on the
    // wordmark, the way back, each demo-account chip, and then the form — top to bottom
    // of the right panel.
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "SDJ" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: /browse the archive/i })).toHaveFocus();
    for (const account of DEMO_ACCOUNTS) {
      await userEvent.tab();
      expect(screen.getByRole("button", { name: account.label })).toHaveFocus();
    }
    await userEvent.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toHaveFocus();
  });

  it("prints the prototype notice above the form, so it is read without scrolling", () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    const notice = screen.getByRole("note");
    expect(notice).toHaveTextContent(/final-project prototype, not an official system/i);
    // DOCUMENT_POSITION_FOLLOWING and nothing else: the form comes after the notice in
    // document order and is not nested inside it.
    expect(notice.compareDocumentPosition(screen.getByLabelText("Email"))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });

  it("fills the email from a demo-account chip but never the password", async () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: "Editor" }));

    expect(screen.getByLabelText("Email")).toHaveValue("editor@sdj.test");
    // The whole point of the chip: it saves the typing it can, and leaves the credential
    // that actually authenticates to the reader — with the cursor already waiting there.
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Editor" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Author" })).toHaveAttribute("aria-pressed", "false");
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
    // Seeded desks belong to signing in; offering one here would contradict the form.
    expect(screen.queryByRole("button", { name: "Author" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    expect(screen.getByRole("heading", { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Full name")).not.toBeInTheDocument();
  });

  it("carries no address across a mode switch", async () => {
    vi.stubGlobal("fetch", signedOut());
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: "Reviewer" }));
    expect(screen.getByLabelText("Email")).toHaveValue("reviewer@sdj.test");

    // The email is the one controlled field, so unlike the rest it survives the form's
    // remount unless it is cleared on purpose — a seeded address must not leak into a
    // registration the reader is about to type by hand.
    await userEvent.click(screen.getByRole("button", { name: /sign up as an author/i }));
    expect(screen.getByLabelText("Email")).toHaveValue("");
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

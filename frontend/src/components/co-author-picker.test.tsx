import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CoAuthorPicker } from "./co-author-picker";

describe("CoAuthorPicker", () => {
  it("resolves an email to a name the submitter must confirm before it becomes a chip", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: "u-42", full_name: "Dr. Efua Danso", affiliation: "University of Ghana" }),
      }),
    );
    const onChange = vi.fn();
    render(<CoAuthorPicker people={[]} onChange={onChange} />);

    await userEvent.type(screen.getByLabelText(/co-authors/i), "efua@ug.edu.gh");
    await userEvent.click(screen.getByRole("button", { name: /look up/i }));

    await waitFor(() => expect(screen.getByText("Dr. Efua Danso")).toBeInTheDocument());
    expect(onChange).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /add as co-author/i }));
    expect(onChange).toHaveBeenCalledWith([{ id: "u-42", full_name: "Dr. Efua Danso", affiliation: "University of Ghana" }]);
  });

  it("shows a plain message when no account matches, not a raw 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    render(<CoAuthorPicker people={[]} onChange={vi.fn()} />);

    await userEvent.type(screen.getByLabelText(/co-authors/i), "nobody@ug.edu.gh");
    await userEvent.click(screen.getByRole("button", { name: /look up/i }));

    await waitFor(() => expect(screen.getByText(/no account is registered/i)).toBeInTheDocument());
  });
});

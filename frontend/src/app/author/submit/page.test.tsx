import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SubmitPage from "./page";
import type { Manuscript } from "@/types/api";

const { push, uploadMock } = vi.hoisted(() => ({ push: vi.fn(), uploadMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/upload", () => ({ uploadFormData: uploadMock }));

const MANUSCRIPT: Manuscript = {
  tracking_code: "SDJ-2026-0007",
  title: "Continuous verification of editorial provenance",
  abstract: "a".repeat(120),
  keywords: ["provenance"],
  author_ids: ["u-1"],
  corresponding_author_id: "u-1",
  status: "submitted",
  version: 1,
  minimum_reviews: 2,
  submitted_reviews: 0,
  has_document: true,
};

async function fillAndSubmit() {
  await userEvent.type(screen.getByLabelText(/^title/i), MANUSCRIPT.title);
  await userEvent.type(screen.getByLabelText(/abstract/i), "An abstract long enough to pass.");
  await userEvent.type(screen.getByLabelText(/keywords/i), "provenance");
  const pdf = new File(["%PDF-1.7"], "paper.pdf", { type: "application/pdf" });
  await userEvent.upload(screen.getByLabelText(/manuscript pdf/i), pdf);
  await userEvent.click(screen.getByRole("button", { name: /submit manuscript/i }));
}

describe("SubmitPage anonymisation preflight", () => {
  beforeEach(() => {
    push.mockClear();
    uploadMock.mockReset();
  });

  it("redirects immediately when the response carries no report — the pre-report backend behaviour", async () => {
    uploadMock.mockResolvedValue({ ok: true, status: 201, data: MANUSCRIPT });
    render(<SubmitPage />);
    await fillAndSubmit();

    await waitFor(() => expect(push).toHaveBeenCalledWith("/author/SDJ-2026-0007?submitted=1"));
    expect(screen.queryByText("Anonymisation report")).not.toBeInTheDocument();
  });

  it("pauses on the report card and only redirects when the author continues", async () => {
    uploadMock.mockResolvedValue({
      ok: true,
      status: 201,
      data: {
        ...MANUSCRIPT,
        anonymisation_report: {
          removed_docinfo_keys: ["/Author"],
          xmp_removed: true,
          author_names_in_body: ["Ama Mensah"],
        },
      },
    });
    render(<SubmitPage />);
    await fillAndSubmit();

    expect(await screen.findByRole("heading", { name: "Anonymisation report" })).toBeInTheDocument();
    expect(screen.getByText(/your name appears in the document body: Ama Mensah/i)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /continue to your manuscript/i }));
    expect(push).toHaveBeenCalledWith("/author/SDJ-2026-0007?submitted=1");
  });
});

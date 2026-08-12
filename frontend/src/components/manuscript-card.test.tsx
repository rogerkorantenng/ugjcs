import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PaperCard } from "./manuscript-card";

const PAPER = {
  tracking_code: "UGJCS-2026-0012",
  title: "Sparse Retrieval for Low-Resource Languages",
  abstract: "An abstract.",
  keywords: ["ir"],
  author_names: ["A. Mensah", "B. Owusu", "C. Boateng"],
  status: "published" as const,
  version: 1,
};

describe("PaperCard", () => {
  it("links to the paper's detail page by tracking code", () => {
    render(<PaperCard paper={PAPER} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/papers/UGJCS-2026-0012");
  });

  it("collapses three or more authors to 'et al.'", () => {
    render(<PaperCard paper={PAPER} />);
    expect(screen.getByText(/A\. Mensah et al\./)).toBeInTheDocument();
  });
});

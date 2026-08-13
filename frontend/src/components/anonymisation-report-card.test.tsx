import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AnonymisationReportCard } from "./anonymisation-report-card";
import type { AnonymisationReport } from "@/types/scholarly";

const CLEAN: AnonymisationReport = { removed_docinfo_keys: [], xmp_removed: false, author_names_in_body: [] };

describe("AnonymisationReportCard", () => {
  it("lists stripped metadata keys and warns in seal tone when a name survives in the body", () => {
    const report: AnonymisationReport = {
      removed_docinfo_keys: ["/Author", "/Creator"],
      xmp_removed: true,
      author_names_in_body: ["Ama Mensah"],
    };
    render(<AnonymisationReportCard report={report} onContinue={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Anonymisation report" })).toBeInTheDocument();
    expect(screen.getByText(/metadata removed:/i)).toBeInTheDocument();
    expect(screen.getByText("/Author, /Creator")).toBeInTheDocument();
    expect(screen.getByText("XMP metadata removed")).toBeInTheDocument();
    // The warning names the author and is honest about what was NOT done.
    expect(screen.getByText(/your name appears in the document body: Ama Mensah/i)).toBeInTheDocument();
    expect(screen.getByText(/body text is not redacted/i)).toBeInTheDocument();
    expect(screen.getByText(/partial detector/i)).toBeInTheDocument();
  });

  it("reports a clean PDF without inventing warnings", () => {
    render(<AnonymisationReportCard report={CLEAN} onContinue={vi.fn()} />);

    expect(screen.getByText("No identifying metadata found")).toBeInTheDocument();
    expect(screen.queryByText(/metadata removed:/i)).not.toBeInTheDocument();
    expect(screen.queryByText("XMP metadata removed")).not.toBeInTheDocument();
    expect(screen.queryByText(/appears in the document body/i)).not.toBeInTheDocument();
  });

  it("hands control back through the one continue button", async () => {
    const onContinue = vi.fn();
    render(<AnonymisationReportCard report={CLEAN} onContinue={onContinue} />);

    await userEvent.click(screen.getByRole("button", { name: /continue to your manuscript/i }));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });
});

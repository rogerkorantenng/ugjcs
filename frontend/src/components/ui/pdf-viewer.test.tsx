import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PdfViewer } from "./pdf-viewer";

const DOCUMENT_URL = "https://s3.example.com/manuscripts/doc.pdf?X-Amz-Expires=300";

function stubDocumentFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ url: DOCUMENT_URL, expires_in_seconds: 300 }),
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window.navigator, "pdfViewerEnabled");
});

describe("PdfViewer", () => {
  it("renders the document inline when the browser reports PDF support", async () => {
    Object.defineProperty(window.navigator, "pdfViewerEnabled", { value: true, configurable: true });
    stubDocumentFetch();

    render(<PdfViewer trackingCode="UGJCS-2026-0001" documentEndpoint="/api/manuscripts/UGJCS-2026-0001/document" title="A Paper" variant="original" />);

    const frame = await waitFor(() => screen.getByTitle("A Paper — PDF preview") as HTMLIFrameElement);
    expect(frame).toHaveAttribute("src", DOCUMENT_URL);
  });

  it("falls back to a prominent Open PDF button instead of an empty frame when inline PDFs aren't supported", async () => {
    Object.defineProperty(window.navigator, "pdfViewerEnabled", { value: false, configurable: true });
    stubDocumentFetch();

    render(<PdfViewer trackingCode="UGJCS-2026-0001" documentEndpoint="/api/manuscripts/UGJCS-2026-0001/document" title="A Paper" variant="original" />);

    await waitFor(() => expect(screen.getByRole("link", { name: /open pdf/i })).toHaveAttribute("href", DOCUMENT_URL));
    expect(screen.queryByTitle("A Paper — PDF preview")).not.toBeInTheDocument();
  });

  it("shows the redaction bar alongside the anonymised viewer, never the author's name", async () => {
    Object.defineProperty(window.navigator, "pdfViewerEnabled", { value: true, configurable: true });
    stubDocumentFetch();

    render(<PdfViewer trackingCode="UGJCS-2026-0003" documentEndpoint="/api/reviews/UGJCS-2026-0003/document" title="Blinded Paper" variant="anonymised" />);

    expect(await screen.findByText(/author withheld/i)).toBeInTheDocument();
  });

  it("offers Reload document rather than a dead frame once the link is treated as expired", async () => {
    vi.useFakeTimers();
    Object.defineProperty(window.navigator, "pdfViewerEnabled", { value: true, configurable: true });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ url: DOCUMENT_URL, expires_in_seconds: 1 }),
      }),
    );

    render(<PdfViewer trackingCode="UGJCS-2026-0001" documentEndpoint="/api/manuscripts/UGJCS-2026-0001/document" title="A Paper" variant="original" />);
    await vi.waitFor(() => expect(screen.getByTitle("A Paper — PDF preview")).toBeInTheDocument());

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(screen.getByRole("button", { name: /reload document/i })).toBeInTheDocument();
    vi.useRealTimers();
  });
});

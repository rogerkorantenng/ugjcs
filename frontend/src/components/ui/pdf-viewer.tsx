"use client";
import { useEffect, useState } from "react";
import { useDocumentUrl } from "@/lib/use-document-url";
import { supportsInlinePdf } from "@/lib/pdf-support";
import { RegistryStamp } from "@/components/ui/registry-stamp";
import { RedactedAuthorSlot } from "@/components/ui/redaction-bar";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

// How long an inline `<iframe>` gets to prove it rendered something before this component
// gives up and offers the fallback button instead. There is no DOM event for "the PDF
// plugin produced a blank page" — cross-origin content can't be introspected — so this is a
// generous ceiling for a genuinely slow load, not a precise render check.
const LOAD_GRACE_MS = 8_000;

interface PdfViewerProps {
  trackingCode: string;
  /** The same-origin BFF route this document's plain download link already uses — this
   * component appends `?format=json` itself so callers never duplicate that detail. */
  documentEndpoint: string;
  title: string;
  variant: "original" | "anonymised";
  className?: string;
}

/**
 * The paper, in a frame, with its accession code — the styled home for the inline document
 * preview asked for on the public paper page, the author's detail page, and the reviewer's
 * page (anonymised endpoint only). Download is offered too, but demoted to a plain text
 * link beside the frame rather than a competing button.
 */
export function PdfViewer({ trackingCode, documentEndpoint, title, variant, className = "" }: PdfViewerProps) {
  const { state, reload } = useDocumentUrl(`${documentEndpoint}?format=json`);
  const [canInline, setCanInline] = useState<boolean | null>(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    setCanInline(supportsInlinePdf());
  }, []);

  useEffect(() => {
    if (state.status !== "ready" || !canInline) return;
    setIframeLoaded(false);
    setTimedOut(false);
    const timer = setTimeout(() => setTimedOut(true), LOAD_GRACE_MS);
    return () => clearTimeout(timer);
  }, [state, canInline]);

  const showFallbackButton =
    state.status === "ready" && (canInline === false || (timedOut && !iframeLoaded));

  return (
    <div className={`rounded-[3px] border border-rule bg-ink/[0.03] p-3 sm:p-4 ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3">
        <div className="flex flex-wrap items-center gap-3">
          <RegistryStamp code={trackingCode} />
          {variant === "anonymised" && <RedactedAuthorSlot className="py-1.5" />}
        </div>
        {state.status === "ready" && (
          <a
            href={documentEndpoint}
            className="text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp"
          >
            Download {variant === "anonymised" ? "anonymised " : ""}PDF
          </a>
        )}
      </div>

      <div className="relative flex min-h-[60vh] items-center justify-center overflow-hidden rounded-[2px] border border-rule bg-surface sm:min-h-[70vh]">
        {state.status === "loading" && (
          <p className="flex items-center gap-2 text-sm text-ink/60">
            <Spinner className="text-stamp" /> Loading document…
          </p>
        )}

        {state.status === "error" && (
          <div className="px-6 text-center">
            <p className="text-sm font-medium text-seal">{state.message}</p>
            <Button variant="secondary" className="mt-3" onClick={reload}>
              Try again
            </Button>
          </div>
        )}

        {state.status === "expired" && (
          <div className="px-6 text-center">
            <p className="text-sm font-medium text-ink">
              This preview link has expired, for the same reason it was short-lived to begin with.
            </p>
            <Button className="mt-3" onClick={reload}>
              Reload document
            </Button>
          </div>
        )}

        {state.status === "ready" && canInline === null && (
          <p className="flex items-center gap-2 text-sm text-ink/60">
            <Spinner className="text-stamp" /> Preparing preview…
          </p>
        )}

        {state.status === "ready" && canInline !== null && (
          <>
            {!showFallbackButton && (
              <iframe
                key={state.url}
                src={state.url}
                title={`${title} — PDF preview`}
                className="h-[60vh] w-full sm:h-[70vh]"
                onLoad={() => setIframeLoaded(true)}
              />
            )}
            {showFallbackButton && (
              <div className="px-6 text-center">
                <p className="text-sm text-ink/70">
                  {canInline === false
                    ? "This browser can't preview PDFs inline. Open it directly instead."
                    : "The preview is taking longer than expected. Open it directly instead."}
                </p>
                <a href={state.url} target="_blank" rel="noreferrer" className="mt-3 inline-block">
                  <Button>Open PDF</Button>
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

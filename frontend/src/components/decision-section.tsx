"use client";
import { DecisionForm } from "@/components/decision-form";
import { DECIDED_STATUSES } from "@/lib/editorial-statuses";
import type { ManuscriptStatus } from "@/types/api";

/**
 * The "Decision" section of the editor's manuscript page: the decision form, and — once
 * a decision has been recorded — a download link for the decision certificate PDF. The
 * link is a plain `<a>` to the streaming BFF route
 * (`/api/editorial-certificate/{trackingCode}`), not a fetch: the browser handles the
 * download natively, and the bearer token stays server-side.
 */
export function DecisionSection({
  trackingCode,
  status,
  onDecided,
}: {
  trackingCode: string;
  status: ManuscriptStatus;
  onDecided: () => void;
}) {
  return (
    <div className="mt-6 border-t border-rule pt-6">
      <h2 className="font-display-heading text-lg font-semibold text-ink">Decision</h2>
      <DecisionForm trackingCode={trackingCode} status={status} onDecided={onDecided} />
      {DECIDED_STATUSES.has(status) && (
        <a
          href={`/api/editorial-certificate/${trackingCode}`}
          className="mt-4 inline-flex items-center gap-1.5 rounded-[3px] text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-2 hover:decoration-stamp focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          Download decision certificate
          <span aria-hidden="true" className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink/45">PDF</span>
        </a>
      )}
    </div>
  );
}

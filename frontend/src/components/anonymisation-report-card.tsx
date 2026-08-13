"use client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AnonymisationReport } from "@/types/scholarly";

/**
 * The post-submission preflight card: what the anonymisation pass actually did to the
 * uploaded PDF, shown *before* the redirect so the one moment an author can still act on
 * it (re-export without their name, resubmit) isn't skipped past. Rendered only when the
 * backend attached `anonymisation_report` — an older backend means an immediate redirect,
 * exactly as before.
 */
export function AnonymisationReportCard({
  report,
  onContinue,
}: {
  report: AnonymisationReport;
  onContinue: () => void;
}) {
  const { removed_docinfo_keys: removedKeys, xmp_removed: xmpRemoved, author_names_in_body: namesInBody } = report;
  return (
    <Card className="mt-6" role="status">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">Blinding preflight</p>
      <h2 className="font-display-heading mt-1 text-lg font-semibold text-ink">Anonymisation report</h2>
      <ul className="mt-3 space-y-1.5 text-sm text-ink/80">
        {removedKeys.length > 0 ? (
          <li>
            <span aria-hidden="true" className="mr-1.5 text-verified">✓</span>
            Metadata removed: <span className="font-mono text-xs">{removedKeys.join(", ")}</span>
          </li>
        ) : (
          !xmpRemoved && (
            <li>
              <span aria-hidden="true" className="mr-1.5 text-verified">✓</span>
              No identifying metadata found
            </li>
          )
        )}
        {xmpRemoved && (
          <li>
            <span aria-hidden="true" className="mr-1.5 text-verified">✓</span>
            XMP metadata removed
          </li>
        )}
      </ul>
      {namesInBody.length > 0 && (
        <div className="mt-4 border-l-2 border-seal bg-seal/5 px-4 py-3">
          <p className="text-sm font-semibold text-seal">
            Your name appears in the document body: {namesInBody.join(", ")}. Metadata was stripped, but body text
            is not redacted — consider re-exporting without it.
          </p>
          <p className="mt-1.5 text-xs text-ink/50">
            This check is a partial detector — it flags exact name matches only, so an absence of warnings is not a
            guarantee of full anonymity.
          </p>
        </div>
      )}
      <Button className="mt-5" onClick={onContinue}>
        Continue to your manuscript
      </Button>
    </Card>
  );
}

/** The whole post-submission screen the submit page swaps to: page heading + report card.
 * Kept here (not on the page) so the submit page stays within the file-size limit. */
export function SubmissionPreflight({ report, onContinue }: { report: AnonymisationReport; onContinue: () => void }) {
  return (
    <>
      <h1 className="font-display-heading text-2xl font-semibold text-ink">Manuscript submitted</h1>
      <AnonymisationReportCard report={report} onContinue={onContinue} />
    </>
  );
}

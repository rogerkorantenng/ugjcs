"use client";
import { use, useState } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { StatusBadge, StatusExplanation } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { BackLink } from "@/components/ui/back-link";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { ReviewerPicker } from "@/components/reviewer-picker";
import { AssignmentsPanel } from "@/components/assignments-panel";
import { DecisionForm } from "@/components/decision-form";
import { PublicationPanel } from "@/components/publication-panel";
import { ReviewsPanel } from "@/components/reviews-panel";
import type { Manuscript, ProblemDetails, SessionUser } from "@/types/api";

const PUBLICATION_STATUSES = new Set(["accepted", "scheduled"]);
// A decision certificate only exists once a decision has been recorded — the backend
// answers 409 before that, so the link renders only from these statuses onward.
const DECIDED_STATUSES = new Set(["accepted", "rejected", "scheduled", "published"]);
// `begin_screening` is legal from both SUBMITTED and RESUBMITTED (`domain/transitions.py`)
// — a resubmission goes through screening again, the same way a first submission does.
const SCREENABLE_STATUSES = new Set(["submitted", "resubmitted"]);
// Reviews only ever exist once a manuscript has left screening for the first time.
const REVIEWABLE_STATUSES = new Set([
  "under_review",
  "reviews_complete",
  "revision_requested",
  "resubmitted",
  "accepted",
  "scheduled",
  "published",
  "rejected",
]);

export default function EditorialManuscriptPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);
  // Only an Editor-in-Chief may schedule or publish (`Action.PUBLISH` in
  // `backend/src/ugjcs/domain/policies.py`); `GET /api/auth/me` is the only place the
  // client learns the signed-in actor's roles.
  const { data: session } = useApi<{ user: SessionUser | null }>("/api/auth/me");
  const isEditorInChief = session?.user?.roles.includes("editor_in_chief") ?? false;
  const [screening, setScreening] = useState(false);
  const [screenProblem, setScreenProblem] = useState<ProblemDetails | null>(null);

  if (isLoading) return <ManuscriptDetailSkeleton label="Loading manuscript…" />;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  if (!data) return null;

  async function screen() {
    setScreening(true);
    setScreenProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/screen`, { method: "POST" });
    setScreening(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setScreenProblem(detail ?? { type: "about:blank", title: "Could not begin screening", status: response.status });
      return;
    }
    mutate();
  }

  return (
    <>
      <BackLink href="/editor" label="Screening queue" />
      <div className="flex items-center justify-between">
        <h1 className="font-display-heading text-2xl font-semibold text-ink">{data.title}</h1>
        <StatusBadge status={data.status} />
      </div>
      <TrackingChip code={data.tracking_code} className="mt-1" />
      <StatusExplanation status={data.status} className="mt-2" />
      <p className="mt-4 leading-relaxed text-ink/80">{data.abstract}</p>
      <p className="mt-4 text-sm text-ink/60">{data.submitted_reviews} of {data.minimum_reviews} reviews submitted</p>

      {data.has_document && (
        <PdfViewer
          trackingCode={data.tracking_code}
          documentEndpoint={`/api/manuscripts/${trackingCode}/document`}
          title={data.title}
          variant="original"
          className="mt-4"
        />
      )}

      {SCREENABLE_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          {screenProblem && (
            <div className="mb-4">
              <ProblemAlert problem={screenProblem} />
            </div>
          )}
          <Button isLoading={screening} onClick={screen}>{screening ? "Starting…" : "Begin screening"}</Button>
        </div>
      )}

      {data.status === "under_screening" && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Assign a reviewer</h2>
          <p className="mt-1 text-sm text-ink/60">
            Candidates who share an affiliation with an author, or who are already at capacity, are shown greyed out
            with the reason — a conflict of interest is visible here, not just silently prevented.
          </p>
          <ReviewerPicker trackingCode={trackingCode} onAssigned={mutate} />
        </div>
      )}

      {(data.status === "under_screening" || REVIEWABLE_STATUSES.has(data.status)) && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Assigned reviewers</h2>
          <AssignmentsPanel trackingCode={trackingCode} />
        </div>
      )}

      {REVIEWABLE_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Reviews</h2>
          <ReviewsPanel trackingCode={trackingCode} />
        </div>
      )}

      <div className="mt-6 border-t border-rule pt-6">
        <h2 className="font-display-heading text-lg font-semibold text-ink">Decision</h2>
        <DecisionForm trackingCode={trackingCode} status={data.status} onDecided={mutate} />
        {DECIDED_STATUSES.has(data.status) && (
          <a
            href={`/api/editorial-certificate/${trackingCode}`}
            className="mt-4 inline-flex items-center gap-1.5 rounded-[3px] text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-2 hover:decoration-stamp focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            Download decision certificate
            <span aria-hidden="true" className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink/45">PDF</span>
          </a>
        )}
      </div>

      {isEditorInChief && PUBLICATION_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Publication</h2>
          <PublicationPanel trackingCode={trackingCode} status={data.status} onChanged={mutate} />
        </div>
      )}
    </>
  );
}

"use client";
import { use } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { StatusBadge, StatusExplanation } from "@/components/ui/badge";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { BackLink } from "@/components/ui/back-link";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { ReviewerPicker } from "@/components/reviewer-picker";
import { DecisionForm } from "@/components/decision-form";
import { PublicationPanel } from "@/components/publication-panel";
import { ReviewsPanel } from "@/components/reviews-panel";
import { ScreenControl } from "@/components/screen-control";
import { ApcPanel } from "@/components/apc-panel";
import { BILLABLE_STATUSES, PUBLICATION_STATUSES, REVIEWABLE_STATUSES } from "@/lib/editorial-statuses";
import type { Manuscript, SessionUser } from "@/types/api";

export default function EditorialManuscriptPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);
  // Only an Editor-in-Chief may schedule or publish (`Action.PUBLISH` in
  // `backend/src/ugjcs/domain/policies.py`); `GET /api/auth/me` is the only place the
  // client learns the signed-in actor's roles.
  const { data: session } = useApi<{ user: SessionUser | null }>("/api/auth/me");
  const isEditorInChief = session?.user?.roles.includes("editor_in_chief") ?? false;

  if (isLoading) return <ManuscriptDetailSkeleton label="Loading manuscript…" />;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  if (!data) return null;

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

      <ScreenControl trackingCode={trackingCode} status={data.status} onScreened={mutate} />

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

      {REVIEWABLE_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Reviews</h2>
          <ReviewsPanel trackingCode={trackingCode} />
        </div>
      )}

      <div className="mt-6 border-t border-rule pt-6">
        <h2 className="font-display-heading text-lg font-semibold text-ink">Decision</h2>
        <DecisionForm trackingCode={trackingCode} status={data.status} onDecided={mutate} />
      </div>

      {BILLABLE_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <ApcPanel trackingCode={trackingCode} variant="editor" canWaive={isEditorInChief} />
        </div>
      )}

      {isEditorInChief && PUBLICATION_STATUSES.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Publication</h2>
          <PublicationPanel trackingCode={trackingCode} status={data.status} onChanged={mutate} />
        </div>
      )}
    </>
  );
}

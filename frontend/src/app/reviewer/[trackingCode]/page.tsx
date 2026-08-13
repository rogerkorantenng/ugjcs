"use client";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { BackLink } from "@/components/ui/back-link";
import { BlindedManuscriptView } from "@/components/blinded-manuscript-view";
import { ReviewForm } from "@/components/review-form";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import type { BlindedManuscript } from "@/types/api";

/**
 * Plan 4 exposes no `GET /reviews/{tracking_code}` detail route — `GET /reviews/mine` is
 * the only read (docs/05-api-contract.md §6). Reusing the same SWR key as the assignments
 * list means this page shares its cache with `/reviewer` rather than issuing a second
 * network call, and finds the one manuscript this reviewer is entitled to see by its
 * tracking code, the only identifier `BlindedManuscript` carries.
 */
export default function ReviewAssignmentPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const router = useRouter();
  const { data, error, isLoading } = useApi<BlindedManuscript[]>("/api/reviews");

  if (isLoading) return <ManuscriptDetailSkeleton label="Loading manuscript…" />;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  const manuscript = data?.find((m) => m.tracking_code === trackingCode);
  if (!manuscript)
    return (
      <ProblemAlert problem={{ type: "about:blank", title: "Assignment not found", status: 404 }} />
    );

  return (
    <>
      <BackLink href="/reviewer" label="My assignments" />
      <BlindedManuscriptView manuscript={manuscript} />
      {/*
        The anonymised copy only, ever — `/api/reviews/{trackingCode}/document` is the one
        document route a reviewer-facing page may link to. It has no `variant` parameter
        on the backend at all, so there is no way to point this viewer at the author's
        original even by mistake; see `frontend/src/app/api/reviews/[trackingCode]/document/route.ts`.
        `PdfViewer`'s `variant="anonymised"` renders the redaction bar alongside the frame —
        the same signature device `BlindedManuscriptView` already showed above it.
      */}
      <PdfViewer
        trackingCode={manuscript.tracking_code}
        documentEndpoint={`/api/reviews/${trackingCode}/document`}
        title={manuscript.title}
        variant="anonymised"
        className="mt-4"
      />
      <div className="mt-6 border-t border-rule pt-6">
        <h2 className="font-display-heading text-lg font-semibold text-ink">Submit your review</h2>
        <ReviewForm trackingCode={trackingCode} onSubmitted={() => router.push("/reviewer?submitted=1")} />
      </div>
    </>
  );
}

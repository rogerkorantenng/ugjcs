"use client";
import { use, useState } from "react";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { BlindedManuscriptView } from "@/components/blinded-manuscript-view";
import { ReviewForm } from "@/components/review-form";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { buttonClasses } from "@/components/ui/button";
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
  const { data, error, isLoading } = useApi<BlindedManuscript[]>("/api/reviews");
  const [submitted, setSubmitted] = useState(false);

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

  // Confirms the outcome and says what happens next, in place, instead of silently routing
  // back to the list — the reviewer just did something they cannot undo (see `ReviewForm`),
  // so the app tells them plainly it landed before it takes them anywhere.
  if (submitted) {
    return (
      <div role="status" className="rounded-[3px] border border-verified/30 bg-verified/[0.06] px-6 py-10 text-center">
        <p className="font-serif text-lg font-semibold text-verified">Review submitted</p>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-ink/70">
          Thank you — your assessment has been recorded and sent to the handling editor. This
          assignment no longer needs anything from you.
        </p>
        <Link href="/reviewer" className={buttonClasses("secondary", "mt-5")}>
          Back to my assignments
        </Link>
      </div>
    );
  }

  return (
    <>
      <BlindedManuscriptView manuscript={manuscript} />
      {/*
        The anonymised copy only, ever — `/api/reviews/{trackingCode}/document` is the one
        document route a reviewer-facing page may link to. It has no `variant` parameter
        on the backend at all, so there is no way to point this link at the author's
        original even by mistake; see `frontend/src/app/api/reviews/[trackingCode]/document/route.ts`.
      */}
      <a
        href={`/api/reviews/${trackingCode}/document`}
        className="mt-4 inline-block text-sm font-medium text-stamp-dark underline underline-offset-2"
      >
        Download anonymised manuscript
      </a>
      <div className="mt-6 border-t border-rule pt-6">
        <h2 className="font-serif text-lg font-semibold text-ink">Submit your review</h2>
        <ReviewForm trackingCode={trackingCode} onSubmitted={() => setSubmitted(true)} />
      </div>
    </>
  );
}

"use client";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { BlindedManuscriptView } from "@/components/blinded-manuscript-view";
import { ReviewForm } from "@/components/review-form";
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

  if (isLoading) return <p>Loading…</p>;
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
      <BlindedManuscriptView manuscript={manuscript} />
      <ReviewForm trackingCode={trackingCode} onSubmitted={() => router.push("/reviewer")} />
    </>
  );
}

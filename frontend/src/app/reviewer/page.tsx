"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { cardLinkClasses } from "@/components/ui/card";
import { ManuscriptListSkeleton } from "@/components/skeletons";
import type { BlindedManuscript } from "@/types/api";

/** See the author dashboard's `SubmittedBanner` for why this is isolated behind its own
 * Suspense boundary rather than calling `useSearchParams()` directly in the page body. */
function SubmittedBanner() {
  if (useSearchParams().get("submitted") !== "1") return null;
  return (
    <div className="mb-6 rounded-[3px] border-l-2 border-stamp bg-stamp/[0.06] px-4 py-3">
      <p className="font-medium text-ink">Review submitted.</p>
      <p className="mt-1 text-sm text-ink/70">
        The handling editor can now see your scores and comments. Your identity stays withheld from the author
        throughout — nothing further is required from you unless a revision is later sent back for another round.
      </p>
    </div>
  );
}

export default function ReviewerAssignments() {
  const { data, error, isLoading } = useApi<BlindedManuscript[]>("/api/reviews");

  return (
    <>
      <Suspense fallback={null}>
        <SubmittedBanner />
      </Suspense>
      <h1 className="font-display-heading text-2xl font-semibold text-ink">My review assignments</h1>

      {isLoading && <ManuscriptListSkeleton withBadge={false} label="Loading your assignments…" />}

      {error && (
        <div className="mt-4">
          <ProblemAlert
            problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
          />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          title="No assignments yet"
          hint="Manuscripts will appear here once an editor assigns you to review them."
        />
      )}

      {data && data.length > 0 && (
        <ul className="mt-4 space-y-3">
          {data.map((manuscript) => (
            <li key={manuscript.tracking_code}>
              <Link href={`/reviewer/${manuscript.tracking_code}`} className={cardLinkClasses()}>
                <p className="font-medium text-ink">{manuscript.title}</p>
                <TrackingChip code={manuscript.tracking_code} className="mt-1" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

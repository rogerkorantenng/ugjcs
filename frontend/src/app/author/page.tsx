"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonClasses } from "@/components/ui/button";
import { cardLinkClasses } from "@/components/ui/card";
import { ManuscriptListSkeleton } from "@/components/skeletons";
import { Tour } from "@/components/tour/tour";
import { AUTHOR_TOUR } from "@/components/tour/steps";
import type { Manuscript } from "@/types/api";

export default function AuthorDashboard() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/manuscripts");

  return (
    <>
      <Tour steps={AUTHOR_TOUR.steps} storageKey={AUTHOR_TOUR.storageKey} />
      <h1 data-tour="author-welcome" className="font-display-heading text-2xl font-semibold text-ink">My submissions</h1>

      {isLoading && <ManuscriptListSkeleton label="Loading your submissions…" />}

      {error && (
        <div className="mt-4">
          <ProblemAlert
            problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
          />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          title="No manuscripts submitted yet"
          hint="Once you submit a manuscript, it appears here with its review status."
          action={<Link href="/author/submit" className={buttonClasses("primary")}>Submit a manuscript</Link>}
        />
      )}

      {data && data.length > 0 && (
        <ul data-tour="author-list" className="mt-4 space-y-3">
          {data.map((manuscript, index) => (
            <li key={manuscript.tracking_code}>
              <Link href={`/author/${manuscript.tracking_code}`} className={cardLinkClasses("flex items-center justify-between")}>
                <div>
                  <p className="font-medium text-ink">{manuscript.title}</p>
                  {/* The first chip doubles as the tour's "tracking codes" anchor. */}
                  <span data-tour={index === 0 ? "author-tracking" : undefined} className="mt-1 inline-block">
                    <TrackingChip code={manuscript.tracking_code} />
                  </span>
                </div>
                <StatusBadge status={manuscript.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { cardLinkClasses } from "@/components/ui/card";
import { ManuscriptListSkeleton } from "@/components/skeletons";
import { RedactionBar } from "@/components/ui/redaction-bar";
import type { BlindedManuscript } from "@/types/api";

export default function ReviewerAssignments() {
  const { data, error, isLoading } = useApi<BlindedManuscript[]>("/api/reviews");

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">My review assignments</h1>
      <p className="mt-1.5 text-sm text-ink/60">
        Every manuscript below is shown to you under double-blind conditions — the author&rsquo;s
        identity is withheld, not merely hidden by this screen.
      </p>

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
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <TrackingChip code={manuscript.tracking_code} />
                  <RedactionBar compact />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

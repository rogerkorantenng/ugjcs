"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonClasses } from "@/components/ui/button";
import { ManuscriptListSkeleton } from "@/components/skeletons";
import type { Manuscript } from "@/types/api";

export default function AuthorDashboard() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/manuscripts");

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">My submissions</h1>

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
        <ul className="mt-4 space-y-3">
          {data.map((manuscript) => (
            <li key={manuscript.tracking_code}>
              <Link
                href={`/author/${manuscript.tracking_code}`}
                className="flex items-center justify-between rounded-[3px] border border-rule bg-white/70 p-4 transition-colors hover:border-teal/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
              >
                <div>
                  <p className="font-medium text-ink">{manuscript.title}</p>
                  <TrackingChip code={manuscript.tracking_code} className="mt-1" />
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

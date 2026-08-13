"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDays, relativeDate } from "@/lib/analytics-format";
import type { ReviewerPerformance } from "@/types/analytics";

const COLUMNS = ["Reviewer", "Affiliation", "Load", "Completed", "Avg turnaround", "Last activity"];

/**
 * The "Reviewer performance" table on `/editor/analytics` — load as n/capacity, completed
 * reviews, average turnaround in days, and last activity as a relative date. Fetches
 * `GET /api/editorial/reviewer-performance` independently of the analytics aggregate.
 */
export function ReviewerPerformanceTable() {
  const { data, error, isLoading } = useApi<ReviewerPerformance[]>("/api/editorial/reviewer-performance");

  return (
    <section className="mt-10">
      <h2 className="font-display-heading text-lg font-semibold text-ink">Reviewer performance</h2>

      {isLoading && (
        <div role="status" aria-live="polite" aria-busy="true" className="mt-3 space-y-2.5">
          <span className="sr-only">Loading reviewer performance…</span>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      )}

      {error && (
        <div className="mt-3">
          <ProblemAlert
            problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Could not load reviewer performance", status: 500 }}
          />
        </div>
      )}

      {data && data.length === 0 && <p className="mt-3 text-sm text-ink/60">No reviewers on the roster yet.</p>}

      {data && data.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <caption className="sr-only">Reviewer load, completed reviews, and turnaround</caption>
            <thead>
              <tr className="border-b border-rule text-ink/60">
                {COLUMNS.map((column) => (
                  <th key={column} scope="col" className="py-2 pr-4 font-medium">{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((reviewer) => (
                <tr key={reviewer.id} className="border-b border-rule">
                  <td className="py-2.5 pr-4 font-medium text-ink">{reviewer.full_name}</td>
                  <td className="pr-4 text-ink/70">{reviewer.affiliation}</td>
                  <td className="pr-4 font-mono text-xs text-ink/80">
                    {reviewer.active_assignments}/{reviewer.reviewer_capacity}
                  </td>
                  <td className="pr-4 font-mono text-xs text-ink/80">{reviewer.reviews_completed}</td>
                  <td className="pr-4 text-ink/70">
                    {reviewer.avg_turnaround_days === null ? "—" : `${formatDays(reviewer.avg_turnaround_days)} days`}
                  </td>
                  <td className="text-ink/70">{relativeDate(reviewer.last_activity_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

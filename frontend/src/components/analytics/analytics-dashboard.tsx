"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiRow } from "@/components/analytics/kpi-row";
import { PipelineBars } from "@/components/analytics/pipeline-bars";
import { MonthChart } from "@/components/analytics/month-chart";
import type { EditorialAnalytics } from "@/types/analytics";

/** Mirrors the loaded layout: three stat tiles, then a stack of pipeline bars. */
function AnalyticsSkeleton() {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">Loading analytics…</span>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-[3px] border border-rule bg-surface/70 p-5">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-3 h-8 w-16" />
          </div>
        ))}
      </div>
      <div className="mt-10 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="grid grid-cols-[10rem_1fr] items-center gap-3">
            <Skeleton className="h-4 w-28" />
            <div style={{ width: `${85 - i * 15}%` }}>
              <Skeleton className="h-2.5 w-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * The data half of `/editor/analytics`: fetches `GET /api/editorial/analytics` and
 * renders the KPI row, the pipeline bars and the monthly submission columns. The
 * reviewer table fetches its own endpoint separately, so one slow aggregate never
 * blocks the other.
 */
export function AnalyticsDashboard() {
  const { data, error, isLoading } = useApi<EditorialAnalytics>("/api/editorial/analytics");

  if (isLoading) return <AnalyticsSkeleton />;
  if (error) {
    return (
      <div className="mt-6">
        <ProblemAlert
          problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Could not load analytics", status: 500 }}
        />
      </div>
    );
  }
  if (!data) return null;

  return (
    <>
      <KpiRow analytics={data} />
      <PipelineBars analytics={data} />
      <MonthChart months={data.submissions_by_month} />
    </>
  );
}

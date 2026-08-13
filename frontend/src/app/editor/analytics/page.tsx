import type { Metadata } from "next";
import { AnalyticsDashboard } from "@/components/analytics/analytics-dashboard";
import { ReviewerPerformanceTable } from "@/components/analytics/reviewer-performance-table";

export const metadata: Metadata = { title: "Analytics" };

/**
 * Server shell for `/editor/analytics`: the static masthead copy renders immediately,
 * while the two client components below each fetch their own endpoint
 * (`/api/editorial/analytics`, `/api/editorial/reviewer-performance`) with their own
 * skeletons — the same shell-plus-SWR shape as the other dashboards. Auth lives in the
 * shared editor layout; role enforcement is the backend's, surfaced as a problem alert.
 */
export default function EditorialAnalyticsPage() {
  return (
    <>
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">Editorial office</p>
      <h1 className="mt-1 font-display-heading text-2xl font-semibold text-ink">Analytics</h1>
      <AnalyticsDashboard />
      <ReviewerPerformanceTable />
    </>
  );
}

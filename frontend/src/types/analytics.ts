// Mirrors the editorial analytics endpoints being built alongside this UI —
// `GET /editorial/analytics`, `GET /editorial/reviewer-performance`,
// `GET /editorial/{trackingCode}/assignments`. Shapes are the agreed contract,
// snake_case included, matching the convention `src/types/api.ts` established.
// Kept in a separate file so this feature never has to touch `api.ts`.

import type { ManuscriptStatus } from "@/types/api";

export interface MonthCount {
  /** ISO year-month, e.g. "2026-08". */
  month: string;
  count: number;
}

/** `GET /editorial/analytics` — editor/EiC only. The three averages and the acceptance
 * rate are `null` until at least one decision/review exists to average over; the UI
 * renders an em-dash for null rather than a fake zero. */
export interface EditorialAnalytics {
  /** Manuscript counts per status. Statuses with no manuscripts may be present as 0 or
   * absent entirely — treat a missing key as 0. */
  pipeline: Partial<Record<ManuscriptStatus, number>>;
  submissions_by_month: MonthCount[];
  acceptance_rate: number | null;
  avg_days_submission_to_decision: number | null;
  avg_days_review_turnaround: number | null;
}

/** One row of `GET /editorial/reviewer-performance`. */
export interface ReviewerPerformance {
  id: string;
  full_name: string;
  affiliation: string;
  active_assignments: number;
  reviewer_capacity: number;
  reviews_completed: number;
  avg_turnaround_days: number | null;
  last_activity_at: string | null;
}

/** One row of `GET /editorial/{trackingCode}/assignments` — who is reviewing this
 * manuscript and where each review stands against its deadline. */
export interface ReviewAssignment {
  reviewer_id: string;
  reviewer_name: string;
  assigned_at: string;
  due_at: string | null;
  submitted: boolean;
  overdue: boolean;
}

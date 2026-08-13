"use client";
import { useApi } from "@/lib/use-api";
import { chipClasses } from "@/components/due-chip";
import type { ReviewAssignment } from "@/types/analytics";

/**
 * The queue's per-row overdue signal. The assignments endpoint is per-manuscript, so
 * this is only mounted on under-review rows — each row lazily fetches its own
 * assignments in parallel (SWR dedupes with the detail page's panel) and chips the row
 * in seal when any review is past its deadline. Deliberately renders nothing while
 * loading or on error: the chip is a supplementary signal on top of the status badge,
 * and a row must never look broken because one aggregate call failed.
 */
export function ReviewOverdueChip({ trackingCode }: { trackingCode: string }) {
  const { data } = useApi<ReviewAssignment[]>(`/api/editorial/${trackingCode}/assignments`);
  if (!data?.some((assignment) => assignment.overdue && !assignment.submitted)) return null;
  return <span className={chipClasses("seal")}>Review overdue</span>;
}

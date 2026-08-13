"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { DueChipBadge } from "@/components/due-chip";
import type { ReviewAssignment } from "@/types/analytics";

function formatAssignedDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/**
 * The editor's "Assigned reviewers" panel on `/editor/[trackingCode]` — who is reviewing
 * this manuscript, when each was assigned, and where each stands against its deadline
 * (via the tested `dueChip()` labels). Editor-only by route: reviewer names are never
 * blinded from the handling editor, only from authors.
 */
export function AssignmentsPanel({ trackingCode }: { trackingCode: string }) {
  const { data, error, isLoading } = useApi<ReviewAssignment[]>(`/api/editorial/${trackingCode}/assignments`);

  if (isLoading) return <p className="mt-3 text-sm text-ink/60">Loading assignments…</p>;
  if (error) {
    return (
      <div className="mt-3">
        <ProblemAlert
          problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Could not load assignments", status: 500 }}
        />
      </div>
    );
  }
  if (!data || data.length === 0) {
    return <p className="mt-3 text-sm text-ink/60">No reviewers have been assigned yet.</p>;
  }

  return (
    <ul className="mt-3 space-y-2">
      {data.map((assignment) => (
        <li
          key={assignment.reviewer_id}
          className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-[3px] border border-rule bg-surface/70 px-4 py-2.5"
        >
          <span className="text-sm">
            <span className="font-medium text-ink">{assignment.reviewer_name}</span>
            <span className="ml-3 text-ink/60">Assigned {formatAssignedDate(assignment.assigned_at)}</span>
          </span>
          <DueChipBadge dueAt={assignment.due_at} submitted={assignment.submitted} />
        </li>
      ))}
    </ul>
  );
}

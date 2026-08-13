import type { ManuscriptStatus } from "@/types/api";
import { NEGATIVE_STATUSES, POSITIVE_STATUSES, STATUS_EXPLANATIONS } from "@/lib/status";

const LABELS: Record<ManuscriptStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  under_screening: "Under screening",
  desk_rejected: "Desk rejected",
  under_review: "Under review",
  reviews_complete: "Reviews complete",
  revision_requested: "Revision requested",
  resubmitted: "Resubmitted",
  accepted: "Accepted",
  rejected: "Rejected",
  scheduled: "Scheduled",
  published: "Published",
  withdrawn: "Withdrawn",
};

// Three tones only, matching the palette contract — `seal` for a negative/terminal outcome,
// `verified` for a positive/settled one, `stamp` for anything still moving through the
// process. Nothing in between reaches for a fourth hue; a status that needs more nuance than
// three tones explains itself in words via `STATUS_EXPLANATIONS`, not via a new colour.
function toneClasses(status: ManuscriptStatus): string {
  if (NEGATIVE_STATUSES.has(status)) return "text-seal before:bg-seal border-seal/25 bg-seal/[0.06]";
  if (POSITIVE_STATUSES.has(status)) return "text-verified before:bg-verified border-verified/25 bg-verified/[0.06]";
  if (status === "draft") return "text-ink/55 before:bg-ink/30 border-rule bg-ink/[0.03]";
  return "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]";
}

export function StatusBadge({ status, className = "" }: { status: ManuscriptStatus; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-xs font-semibold uppercase tracking-wide before:h-1.5 before:w-1.5 before:rounded-full
        before:content-[''] ${toneClasses(status)} ${className}`}
    >
      {LABELS[status]}
    </span>
  );
}

/** The sentence every `StatusBadge` should be paired with — "statuses should explain
 * themselves rather than name themselves". A plain caption, not a tooltip: it must be
 * visible without a hover, on a touchscreen included. */
export function StatusExplanation({ status, className = "" }: { status: ManuscriptStatus; className?: string }) {
  return <p className={`text-sm text-ink/60 ${className}`}>{STATUS_EXPLANATIONS[status]}</p>;
}

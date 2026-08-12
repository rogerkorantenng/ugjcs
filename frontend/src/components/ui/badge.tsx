import type { ManuscriptStatus } from "@/types/api";

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

// An outlined pill with a coloured dot, not a solid fill block — a screening queue of a
// dozen badges should read as a calm list, not a wall of colour. `text-*` carries the
// tone (>= 4.5:1 against `bg-paper`, WCAG 2.1 AA, checked against the rendered palette);
// `before:bg-*` colours only the 6px dot.
const TONES: Record<ManuscriptStatus, string> = {
  draft: "text-ink/60 before:bg-ink/30",
  submitted: "text-teal-dark before:bg-teal",
  under_screening: "text-teal-dark before:bg-teal",
  desk_rejected: "text-brick before:bg-brick",
  under_review: "text-teal-dark before:bg-teal",
  reviews_complete: "text-teal-dark before:bg-teal",
  revision_requested: "text-amber before:bg-amber",
  resubmitted: "text-amber before:bg-amber",
  accepted: "text-moss before:bg-moss",
  rejected: "text-brick before:bg-brick",
  scheduled: "text-amber before:bg-amber",
  published: "text-moss before:bg-moss",
  withdrawn: "text-ink/60 before:bg-ink/30",
};

export function StatusBadge({ status }: { status: ManuscriptStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-rule px-2.5 py-0.5
        text-xs font-semibold uppercase tracking-wide before:h-1.5 before:w-1.5 before:rounded-full
        before:content-[''] ${TONES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}

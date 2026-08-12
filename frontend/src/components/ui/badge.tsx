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

// A tinted pill with a coloured dot, not a solid fill block — a screening queue of a
// dozen badges should read as a calm list, not a wall of colour. `text-*` carries the
// tone (>= 4.5:1 against `bg-paper`, WCAG 2.1 AA, checked against the rendered palette);
// `before:bg-*` colours the 6px dot; `border-*`/`bg-*` add just enough tint to separate
// one status from the next at a glance, without competing with the dot for attention.
const TONES: Record<ManuscriptStatus, string> = {
  draft: "text-ink/60 before:bg-ink/30 border-rule bg-ink/[0.03]",
  submitted: "text-teal-dark before:bg-teal border-teal/25 bg-teal/[0.06]",
  under_screening: "text-teal-dark before:bg-teal border-teal/25 bg-teal/[0.06]",
  desk_rejected: "text-brick before:bg-brick border-brick/25 bg-brick/[0.06]",
  under_review: "text-teal-dark before:bg-teal border-teal/25 bg-teal/[0.06]",
  reviews_complete: "text-teal-dark before:bg-teal border-teal/25 bg-teal/[0.06]",
  revision_requested: "text-amber before:bg-amber border-amber/30 bg-amber/[0.08]",
  resubmitted: "text-amber before:bg-amber border-amber/30 bg-amber/[0.08]",
  accepted: "text-moss before:bg-moss border-moss/25 bg-moss/[0.06]",
  rejected: "text-brick before:bg-brick border-brick/25 bg-brick/[0.06]",
  scheduled: "text-amber before:bg-amber border-amber/30 bg-amber/[0.08]",
  published: "text-moss before:bg-moss border-moss/25 bg-moss/[0.06]",
  withdrawn: "text-ink/60 before:bg-ink/30 border-rule bg-ink/[0.03]",
};

export function StatusBadge({ status }: { status: ManuscriptStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-xs font-semibold uppercase tracking-wide before:h-1.5 before:w-1.5 before:rounded-full
        before:content-[''] ${TONES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}

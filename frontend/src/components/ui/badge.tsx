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

/**
 * A plain-English sentence for every status — so a reader never has to learn a glossary to
 * know what "reviews complete" or "desk rejected" means for them. Exported so any detail
 * page can put the sentence directly under the badge, not just the label.
 */
export const STATUS_DESCRIPTIONS: Record<ManuscriptStatus, string> = {
  draft: "Not yet submitted.",
  submitted: "Received. Waiting to begin editorial screening.",
  under_screening: "An editor is checking it meets the journal's basic requirements.",
  desk_rejected: "Did not pass initial screening — it was not sent to reviewers.",
  under_review: "With two reviewers now, under double-blind conditions.",
  reviews_complete: "Both reviews are in. An editor is deciding what happens next.",
  revision_requested: "Reviewers asked for changes. Waiting on the author to resubmit.",
  resubmitted: "A revised version is in. An editor will screen it or send it back to review.",
  accepted: "Accepted for publication. Waiting to be scheduled into an issue.",
  rejected: "Not accepted for publication.",
  scheduled: "Scheduled. Will appear in the public archive once published.",
  published: "Published and available in the public archive.",
  withdrawn: "Withdrawn by the author.",
};

// Three tones only, each meaning one thing everywhere it appears: `stamp` (violet) is
// "in motion — something is actively happening or someone owes an action", `seal` (red) is
// "closed, negatively", `verified` (green) is "settled, positively". `draft`/`withdrawn`
// get the neutral ink tone because nothing is in motion. A dozen statuses collapse to a
// three-colour vocabulary a reader can learn once, rather than a rainbow of one-off hues.
const TONES: Record<ManuscriptStatus, string> = {
  draft: "text-ink/55 before:bg-ink/30 border-rule bg-ink/[0.03]",
  submitted: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  under_screening: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  desk_rejected: "text-seal before:bg-seal border-seal/25 bg-seal/[0.06]",
  under_review: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  reviews_complete: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  revision_requested: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  resubmitted: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  accepted: "text-verified before:bg-verified border-verified/25 bg-verified/[0.06]",
  rejected: "text-seal before:bg-seal border-seal/25 bg-seal/[0.06]",
  scheduled: "text-verified before:bg-verified border-verified/25 bg-verified/[0.06]",
  published: "text-verified before:bg-verified border-verified/25 bg-verified/[0.06]",
  withdrawn: "text-ink/55 before:bg-ink/30 border-rule bg-ink/[0.03]",
};

export function StatusBadge({ status, className = "" }: { status: ManuscriptStatus; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-xs font-semibold uppercase tracking-wide before:h-1.5 before:w-1.5 before:rounded-full
        before:content-[''] ${TONES[status]} ${className}`}
    >
      {LABELS[status]}
    </span>
  );
}

/** The badge plus its one-sentence meaning, stacked — what every manuscript detail page
 * (author, editor, reviewer) renders instead of a bare badge, so status is legible without
 * a glossary at the one place a reader is most likely to ask "what does this mean for me". */
export function StatusExplainer({ status }: { status: ManuscriptStatus }) {
  return (
    <div>
      <StatusBadge status={status} />
      <p className="mt-1.5 text-sm leading-relaxed text-ink/65">{STATUS_DESCRIPTIONS[status]}</p>
    </div>
  );
}

import type { ManuscriptStatus } from "@/types/api";

/**
 * A status name alone ("resubmitted") does not say who needs to act next. Every list and
 * detail page that renders a `StatusBadge` renders this sentence directly underneath it —
 * "statuses should explain themselves rather than name themselves". Single source of truth
 * so the explanation on the author's dashboard, the editor's queue and a manuscript detail
 * page can never drift from one another.
 */
export const STATUS_EXPLANATIONS: Record<ManuscriptStatus, string> = {
  draft: "Not yet submitted — only visible to you.",
  submitted: "Received and accession-stamped. Waiting for an editor to begin screening.",
  under_screening: "An editor is deciding whether to desk reject or send this to review.",
  desk_rejected: "Rejected at screening, before review. This is final.",
  under_review: "With reviewers under double-blind conditions. No action needed from you yet.",
  reviews_complete: "All reviews are in. Waiting for the handling editor's decision.",
  revision_requested: "The editor has asked for changes before this can proceed.",
  resubmitted: "A revised version is in. Waiting for the editor to screen it or send it back to review.",
  accepted: "Accepted for publication. Waiting to be scheduled into an issue.",
  rejected: "Not accepted for publication. This is final.",
  scheduled: "Scheduled into an upcoming issue, not yet publicly visible.",
  published: "Published and publicly readable in the archive.",
  withdrawn: "Withdrawn by the author. This is final.",
};

/** Whether reaching this status closes the manuscript's story — no further editorial action
 * is possible. Used to render a full stop rather than an ellipsis in status microcopy, and
 * to decide whether a status badge should read as routine or as a terminal outcome. */
export const TERMINAL_STATUSES = new Set<ManuscriptStatus>([
  "desk_rejected",
  "rejected",
  "withdrawn",
  "published",
]);

/** Whether this status represents an outcome the reader should read as a setback rather than
 * progress — used to keep a destructive-toned badge visually apart from a routine one. */
export const NEGATIVE_STATUSES = new Set<ManuscriptStatus>(["desk_rejected", "rejected", "withdrawn"]);

export const POSITIVE_STATUSES = new Set<ManuscriptStatus>(["accepted", "scheduled", "published"]);

import type { ManuscriptStatus } from "@/types/api";

// Which editorial affordances render for which manuscript status — the single source the
// editor detail page's sections switch on. Each set mirrors a rule that actually lives
// in the backend (`domain/transitions.py`, `domain/policies.py`); the UI only decides
// what to show, never what is legal.

// `begin_screening` is legal from both SUBMITTED and RESUBMITTED (`domain/transitions.py`)
// — a resubmission goes through screening again, the same way a first submission does.
export const SCREENABLE_STATUSES = new Set<ManuscriptStatus>(["submitted", "resubmitted"]);

// Reviews only ever exist once a manuscript has left screening for the first time.
export const REVIEWABLE_STATUSES = new Set<ManuscriptStatus>([
  "under_review",
  "reviews_complete",
  "revision_requested",
  "resubmitted",
  "accepted",
  "scheduled",
  "published",
  "rejected",
]);

export const PUBLICATION_STATUSES = new Set<ManuscriptStatus>(["accepted", "scheduled"]);

// A decision certificate only exists once a decision has been recorded — the backend
// answers 409 before that, so the download link renders only from these statuses onward.
export const DECIDED_STATUSES = new Set<ManuscriptStatus>(["accepted", "rejected", "scheduled", "published"]);

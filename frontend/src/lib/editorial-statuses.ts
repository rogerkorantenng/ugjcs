import type { ManuscriptStatus } from "@/types/api";

/** Only an Editor-in-Chief may schedule or publish (`Action.PUBLISH` in
 * `backend/src/ugjcs/domain/policies.py`). */
export const PUBLICATION_STATUSES = new Set<ManuscriptStatus>(["accepted", "scheduled"]);

/** `begin_screening` is legal from both SUBMITTED and RESUBMITTED (`domain/transitions.py`)
 * — a resubmission goes through screening again, the same way a first submission does. */
export const SCREENABLE_STATUSES = new Set<ManuscriptStatus>(["submitted", "resubmitted"]);

/** Reviews only ever exist once a manuscript has left screening for the first time. */
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

/** An APC invoice can only exist once acceptance is on the record — earlier statuses have
 * nothing to bill, so the APC panel (and its billing fetch) never appears before then. */
export const BILLABLE_STATUSES = new Set<ManuscriptStatus>(["accepted", "scheduled", "published"]);

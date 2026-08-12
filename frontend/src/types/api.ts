// Every type in this file mirrors Plan 4's Pydantic response models field-for-field,
// snake_case included — see docs/05-api-contract.md for the naming-convention decision
// and the full endpoint-by-endpoint diff this file was reconciled against.

export const MANUSCRIPT_STATUSES = [
  "draft", "submitted", "under_screening", "desk_rejected", "under_review",
  "reviews_complete", "revision_requested", "resubmitted", "accepted",
  "rejected", "scheduled", "published", "withdrawn",
] as const;
export type ManuscriptStatus = (typeof MANUSCRIPT_STATUSES)[number];

// Plan 4's `SubmitReviewRequest.recommendation` is an unvalidated `str`, not this domain
// enum — this list is used only to populate the review form's `<select>`, so a value
// outside it is a UI bug, not something the server would ever reject with a 422.
export const RECOMMENDATIONS = ["accept", "minor_revision", "major_revision", "reject"] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export const DECISION_TYPES = [
  "desk_reject", "send_to_review", "request_revision", "accept", "reject",
] as const;
export type DecisionType = (typeof DECISION_TYPES)[number];

export type Role = "author" | "reviewer" | "editor" | "editor_in_chief" | "administrator";

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
}

/**
 * No `name` field: `GET /auth/me` (`ActorOut`) serialises only `{id, roles}` — `Actor`
 * carries nothing else. `email` is not part of that response either; the session's `email`
 * is the value the BFF already validated out of the login request body, not anything the
 * backend echoes back. See docs/05-api-contract.md §1 and §8 (technical debt).
 */
export interface SessionUser {
  id: string;
  email: string;
  roles: Role[];
}

/**
 * Mirrors `ManuscriptOut` exactly — the one shape Plan 4 returns from every manuscript
 * route (`POST /manuscripts`, `GET /manuscripts/mine`, `GET /manuscripts/{trackingCode}`,
 * `POST /manuscripts/{trackingCode}/withdraw`, `POST /manuscripts/{trackingCode}/resubmit`,
 * `GET /editorial/queue`, `POST /editorial/{trackingCode}/schedule`,
 * `POST /editorial/{trackingCode}/publish`). There is no separate "summary" and "detail"
 * shape on the backend, so there is only one type here.
 *
 * `has_document` was added to the live API alongside file upload (docs/05-api-contract.md
 * §8 previously recorded "no file upload ... exists anywhere in the domain" — that gap is
 * now closed; see the frontend wiring notes for the discrepancy).
 *
 * Deliberately absent, because the API does not serialise them anywhere: `id` (the
 * `tracking_code` string is the only identifier the wire ever carries — use it as the
 * React key and the route param), `submitted_at`/`updated_at` (no response carries a
 * timestamp), and `events`/an audit trail (no endpoint exposes one).
 */
export interface Manuscript {
  tracking_code: string;
  title: string;
  abstract: string;
  keywords: string[];
  author_ids: string[];
  corresponding_author_id: string;
  status: ManuscriptStatus;
  version: number;
  minimum_reviews: number;
  submitted_reviews: number;
  has_document: boolean;
}

/**
 * The reviewer-facing projection — mirrors `ugjcs.domain.blinding.BlindedManuscript`
 * field-for-field. There is deliberately no `author_ids`/`corresponding_author_id` field
 * on this type, and no `id` or `document_url` either: Plan 4 stores no document of any
 * kind, so there is nothing to link to. `tracking_code` is this type's only identifier.
 */
export interface BlindedManuscript {
  tracking_code: string;
  title: string;
  abstract: string;
  keywords: string[];
  version: number;
  status: ManuscriptStatus;
}

/**
 * Mirrors `ArchivePaperOut` — Plan 4's public archive shape. `author_names` are resolved
 * server-side (never a raw account id, on a route anyone on the internet can call).
 * Deliberately absent: `published_at`, `doi`, `pdf_url`, `volume`, `number` — none of
 * these exist anywhere in the domain built by Plans 1–4.
 */
export interface ArchivePaperOut {
  tracking_code: string;
  title: string;
  abstract: string;
  keywords: string[];
  author_names: string[];
  status: ManuscriptStatus;
  version: number;
}

/**
 * Mirrors `DocumentUrlOut` — a short-lived, pre-signed link to a stored document, returned
 * by `GET /manuscripts/{trackingCode}/document` and `GET /reviews/{trackingCode}/document`.
 * The live API answers with this JSON body (200), not an HTTP redirect; the BFF route
 * handlers for both endpoints fetch it server-side and turn it into a redirect for the
 * browser to follow, so no page ever needs this type directly.
 */
export interface DocumentUrlOut {
  url: string;
  expires_in_seconds: number;
}

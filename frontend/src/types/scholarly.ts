// Types for the scholarly-infrastructure additions (DOI, citation export, provenance
// verification, anonymisation preflight). These mirror backend shapes that are being
// deployed in parallel — every new field is optional where the page must keep working
// against the older API, so nothing here blocks on the backend landing first.

import type { ArchivePaperOut, Manuscript } from "@/types/api";

/**
 * `ArchivePaperOut` once the backend starts minting DOIs (e.g. `10.55555/sdj.2026.0004`).
 * `doi` stays optional deliberately: the public paper page renders fine against the
 * pre-DOI API and simply omits the DOI line until the field appears on the wire.
 */
export type ScholarlyPaper = ArchivePaperOut & { doi?: string };

/** One hash-chained editorial event, as `GET /archive/{code}/provenance` serialises it. */
export interface ProvenanceEvent {
  sequence: number;
  event_type: string;
  occurred_at: string;
  hash_prefix: string;
}

/**
 * `GET /archive/{code}/provenance` — public, published-only. `intact` is the backend's
 * live re-verification of the hash chain; `head_hash` is the full hex digest of the
 * newest event, shown so a reader can compare it against an independently recorded copy.
 */
export interface ProvenanceOut {
  tracking_code: string;
  intact: boolean;
  head_hash: string;
  events: ProvenanceEvent[];
}

/**
 * What the anonymisation pass did to an uploaded PDF, returned inside the 201 body of
 * `POST /manuscripts` (and on resubmit). `author_names_in_body` is a *partial* detector —
 * metadata is stripped for real, but body text is only scanned, never redacted.
 */
export interface AnonymisationReport {
  removed_docinfo_keys: string[];
  xmp_removed: boolean;
  author_names_in_body: string[];
}

/**
 * The submit response once the backend attaches the report. Optional for the same reason
 * as `doi`: an older backend answers without it and the submit flow must behave exactly
 * as before (immediate redirect, no card).
 */
export type SubmittedManuscript = Manuscript & { anonymisation_report?: AnonymisationReport };

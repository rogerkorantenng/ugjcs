// Wave-2 contracts: APC billing, the admin console, and full-text search snippets.
// Same rule as `types/api.ts` — every type mirrors the backend response field-for-field,
// snake_case included. These endpoints are being built in parallel with this UI, so every
// consumer must degrade gracefully (an error panel, never a blank screen) when one 404s.

import type { ArchivePaperOut, Role } from "@/types/api";

export const BILLING_STATUSES = ["pending", "paid", "waived"] as const;
export type BillingStatus = (typeof BILLING_STATUSES)[number];

/**
 * `GET /billing/{trackingCode}` — the article processing charge for an accepted
 * manuscript. A 404 means no invoice has been raised, which is a normal state (the
 * manuscript may simply not be far enough along), not a failure.
 */
export interface BillingInvoice {
  /** Minor units — 15000 pesewas renders as "GHS 150.00". */
  amount_pesewas: number;
  status: BillingStatus;
  paystack_reference: string | null;
  settled_at: string | null;
}

/**
 * `POST /billing/{trackingCode}/initialize` — either a Paystack checkout redirect
 * (`authorization_url`) or `{"mock": true}`, meaning the mock gateway settled the charge
 * instantly and the invoice should simply be refetched.
 */
export interface BillingInitializeOut {
  authorization_url?: string;
  mock?: boolean;
}

/** One row of `GET /admin/accounts` — administrator only. */
export interface AdminAccount {
  id: string;
  email: string;
  full_name: string;
  affiliation: string;
  roles: Role[];
  reviewer_capacity: number;
  is_active: boolean;
  is_verified: boolean;
}

/**
 * An `/archive/search` hit. `snippet` is present (and non-null) only when the match came
 * from the indexed full text rather than the title/abstract/keywords — optional so this
 * type stays valid against backends deployed before full-text search shipped.
 */
export interface ArchiveSearchHit extends ArchivePaperOut {
  snippet?: string | null;
}

import { Skeleton } from "@/components/ui/skeleton";
import type { BillingStatus } from "@/types/wave2";

export function formatPesewas(amountPesewas: number): string {
  return `GHS ${(amountPesewas / 100).toFixed(2)}`;
}

// Same three-tone rule as `StatusBadge`: stamp while money is still owed, verified once it
// is settled, and a muted ink for waived — a charge that no longer exists, not a success.
const CHIP_TONES: Record<BillingStatus, string> = {
  pending: "text-stamp before:bg-stamp border-stamp/25 bg-stamp/[0.06]",
  paid: "text-verified before:bg-verified border-verified/25 bg-verified/[0.06]",
  waived: "text-ink/55 before:bg-ink/30 border-rule bg-ink/[0.03]",
};

export const BILLING_EXPLANATIONS: Record<BillingStatus, string> = {
  pending: "The article processing charge has not been settled yet.",
  paid: "The article processing charge has been settled via Paystack.",
  waived: "The Editor-in-Chief waived this charge — nothing is owed.",
};

export function BillingChip({ status }: { status: BillingStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-xs font-semibold uppercase tracking-wide before:h-1.5 before:w-1.5 before:rounded-full
        before:content-[''] ${CHIP_TONES[status]}`}
    >
      {status}
    </span>
  );
}

/** The panel's constant frame: mono eyebrow + display heading, whatever the state inside. */
export function ApcShell({ children }: { children: React.ReactNode }) {
  return (
    <section aria-label="Article processing charge">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink/50">Billing</p>
      <h2 className="font-display-heading mt-0.5 text-lg font-semibold text-ink">Article processing charge</h2>
      {children}
    </section>
  );
}

export function ApcSkeleton() {
  return (
    <div role="status" aria-live="polite" aria-busy="true" className="mt-3">
      <span className="sr-only">Loading the article processing charge…</span>
      <div className="flex items-center gap-3">
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="mt-2 h-3.5 w-64 max-w-full" />
    </div>
  );
}

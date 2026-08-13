"use client";
import { useState } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { ApcShell, ApcSkeleton, BillingChip, BILLING_EXPLANATIONS, formatPesewas } from "@/components/apc-parts";
import { WaiveControl } from "@/components/apc-waive";
import type { ProblemDetails } from "@/types/api";
import type { BillingInitializeOut, BillingInvoice } from "@/types/wave2";

/**
 * The APC invoice for an accepted/scheduled/published manuscript. The author variant offers
 * "Pay with Paystack"; the editor variant is a read-only summary plus — Editor-in-Chief
 * only (`canWaive`) — a two-step "Waive charge". A 404 from the billing endpoint means no
 * invoice has been raised (or billing has not been deployed yet), so it renders as a quiet
 * note, never a broken panel.
 */
export function ApcPanel({
  trackingCode,
  variant,
  canWaive = false,
}: {
  trackingCode: string;
  variant: "author" | "editor";
  canWaive?: boolean;
}) {
  const { data, error, isLoading, mutate } = useApi<BillingInvoice>(`/api/billing/${trackingCode}`);
  const [paying, setPaying] = useState(false);
  const [mockPaid, setMockPaid] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  if (isLoading) return <ApcShell><ApcSkeleton /></ApcShell>;
  if (error) {
    if (error instanceof ClientApiError && error.problem.status === 404) {
      return (
        <ApcShell>
          <p className="mt-2 text-sm text-ink/60">No processing charge has been raised for this manuscript yet.</p>
        </ApcShell>
      );
    }
    const fallback = { type: "about:blank", title: "Could not load the article processing charge", status: 500 };
    return (
      <ApcShell>
        <div className="mt-3">
          <ProblemAlert problem={error instanceof ClientApiError ? error.problem : fallback} />
        </div>
      </ApcShell>
    );
  }
  if (!data) return null;

  async function pay() {
    setPaying(true);
    setProblem(null);
    const response = await fetch(`/api/billing/${trackingCode}/initialize`, { method: "POST" });
    if (!response.ok) {
      setPaying(false);
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not start the payment", status: response.status });
      return;
    }
    const result = (await response.json()) as BillingInitializeOut;
    if (result.authorization_url) {
      // Leave `paying` set — the whole page is about to navigate to Paystack's checkout.
      window.location.assign(result.authorization_url);
      return;
    }
    setPaying(false);
    if (result.mock) {
      // The mock gateway settles instantly: no redirect, the invoice is already paid.
      setMockPaid(true);
      mutate();
    }
  }

  return (
    <ApcShell>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <span className="font-display-heading text-xl font-semibold text-ink">{formatPesewas(data.amount_pesewas)}</span>
        <BillingChip status={data.status} />
      </div>
      <p className="mt-1.5 text-sm text-ink/60">{BILLING_EXPLANATIONS[data.status]}</p>
      {mockPaid && <p className="mt-1.5 text-sm font-medium text-verified">Paid (mock gateway)</p>}
      {data.paystack_reference && (
        <p className="mt-1.5 font-mono text-xs text-ink/60">Paystack reference {data.paystack_reference}</p>
      )}
      {data.settled_at && (
        <p className="mt-1 text-xs text-ink/50">
          Settled {new Date(data.settled_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
        </p>
      )}
      {problem && (
        <div className="mt-3">
          <ProblemAlert problem={problem} />
        </div>
      )}
      {variant === "author" && data.status === "pending" && (
        <Button className="mt-4" isLoading={paying} onClick={pay}>
          {paying ? "Contacting Paystack…" : "Pay with Paystack"}
        </Button>
      )}
      {variant === "editor" && canWaive && data.status === "pending" && (
        <WaiveControl trackingCode={trackingCode} amountPesewas={data.amount_pesewas} onWaived={mutate} />
      )}
    </ApcShell>
  );
}

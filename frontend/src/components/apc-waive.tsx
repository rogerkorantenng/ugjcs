"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { formatPesewas } from "@/components/apc-parts";
import type { ProblemDetails } from "@/types/api";

/**
 * The Editor-in-Chief's "Waive charge" control — the same two-step confirmation every
 * other irreversible action in the portal requires, never a single click.
 */
export function WaiveControl({
  trackingCode,
  amountPesewas,
  onWaived,
}: {
  trackingCode: string;
  amountPesewas: number;
  onWaived: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [waiving, setWaiving] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function waive() {
    setWaiving(true);
    setProblem(null);
    const response = await fetch(`/api/billing/${trackingCode}/waive`, { method: "POST" });
    setWaiving(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not waive the charge", status: response.status });
      return;
    }
    setConfirming(false);
    onWaived();
  }

  if (!confirming) {
    return (
      <>
        {problem && (
          <div className="mt-3">
            <ProblemAlert problem={problem} />
          </div>
        )}
        <Button variant="secondary" className="mt-4" onClick={() => setConfirming(true)}>
          Waive charge
        </Button>
      </>
    );
  }
  return (
    <div className="mt-4 rounded-[3px] border-l-2 border-seal bg-seal/[0.05] px-4 py-3">
      {problem && (
        <div className="mb-3">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <p className="text-sm font-medium text-ink">
        Waiving is permanent — the {formatPesewas(amountPesewas)} charge is cancelled and the author will never be
        asked to pay it.
      </p>
      <div className="mt-3 flex gap-3">
        <Button variant="danger" isLoading={waiving} onClick={waive}>
          {waiving ? "Waiving…" : "Confirm waiver"}
        </Button>
        <Button variant="secondary" disabled={waiving} onClick={() => setConfirming(false)}>
          Keep the charge
        </Button>
      </div>
    </div>
  );
}

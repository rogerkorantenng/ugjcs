"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { ManuscriptStatus, ProblemDetails } from "@/types/api";

const WITHDRAWABLE = new Set<ManuscriptStatus>([
  "submitted", "under_screening", "under_review", "reviews_complete", "revision_requested",
]);

/**
 * The author's "Withdraw submission" flow, extracted whole from the detail page.
 * Withdrawal is terminal — the same two-step confirmation the editor's destructive
 * decisions already require, not a single click on an irreversible action. Renders
 * nothing once the manuscript has moved past the statuses withdrawal is legal from.
 */
export function WithdrawControl({
  trackingCode,
  status,
  onWithdrawn,
}: {
  trackingCode: string;
  status: ManuscriptStatus;
  onWithdrawn: () => void;
}) {
  const [withdrawing, setWithdrawing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  if (!WITHDRAWABLE.has(status)) return null;

  async function withdraw() {
    setWithdrawing(true);
    setProblem(null);
    const response = await fetch(`/api/manuscripts/${trackingCode}/withdraw`, { method: "POST" });
    setWithdrawing(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not withdraw the submission", status: response.status });
      return;
    }
    onWithdrawn();
  }

  return (
    <>
      {problem && (
        <div className="mt-4">
          <ProblemAlert problem={problem} />
        </div>
      )}
      {!confirming && (
        <Button variant="danger" className="mt-4" onClick={() => setConfirming(true)}>
          Withdraw submission
        </Button>
      )}
      {confirming && (
        <div className="mt-4 rounded-[3px] border-l-2 border-seal bg-seal/[0.05] px-4 py-3">
          <p className="text-sm font-medium text-ink">
            Withdrawing is permanent. The manuscript leaves the editorial process and cannot be
            reinstated — a new submission would receive a new tracking code.
          </p>
          <div className="mt-3 flex gap-3">
            <Button variant="danger" isLoading={withdrawing} onClick={withdraw}>
              {withdrawing ? "Withdrawing…" : "Confirm withdrawal"}
            </Button>
            <Button variant="secondary" disabled={withdrawing} onClick={() => setConfirming(false)}>
              Keep the submission
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

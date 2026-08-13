"use client";
import { use, useState } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge, STATUS_DESCRIPTIONS } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { Button, buttonClasses } from "@/components/ui/button";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { ResubmitForm } from "@/components/resubmit-form";
import type { Manuscript, ProblemDetails } from "@/types/api";

const WITHDRAWABLE = new Set(["submitted", "under_screening", "under_review", "reviews_complete", "revision_requested"]);

export default function ManuscriptDetailPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);
  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawProblem, setWithdrawProblem] = useState<ProblemDetails | null>(null);

  if (isLoading) return <ManuscriptDetailSkeleton label="Loading manuscript…" />;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  if (!data) return null;

  async function withdraw() {
    setWithdrawing(true);
    setWithdrawProblem(null);
    const response = await fetch(`/api/manuscripts/${trackingCode}/withdraw`, { method: "POST" });
    setWithdrawing(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setWithdrawProblem(detail ?? { type: "about:blank", title: "Could not withdraw the submission", status: response.status });
      return;
    }
    setConfirmingWithdraw(false);
    mutate();
  }

  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <h1 className="font-serif text-2xl font-semibold text-ink">{data.title}</h1>
        <StatusBadge status={data.status} className="shrink-0" />
      </div>
      <TrackingChip code={data.tracking_code} className="mt-2" />
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink/65">{STATUS_DESCRIPTIONS[data.status]}</p>
      <p className="mt-6 leading-relaxed text-ink/80">{data.abstract}</p>
      <p className="mt-4 text-sm text-ink/60">
        {data.submitted_reviews} of {data.minimum_reviews} reviews submitted
      </p>
      {data.has_document && (
        <a href={`/api/manuscripts/${trackingCode}/document`} className={buttonClasses("secondary", "mt-4")}>
          Download my submitted document
        </a>
      )}

      {data.status === "revision_requested" && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-serif text-lg font-semibold text-ink">Resubmit a revised manuscript</h2>
          <ResubmitForm trackingCode={trackingCode} onResubmitted={mutate} />
        </div>
      )}

      {WITHDRAWABLE.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          {withdrawProblem && (
            <div className="mb-4">
              <ProblemAlert problem={withdrawProblem} />
            </div>
          )}
          {!confirmingWithdraw ? (
            <Button variant="danger" onClick={() => setConfirmingWithdraw(true)}>
              Withdraw submission
            </Button>
          ) : (
            // Irreversible, so it looks and behaves differently from a routine action: a
            // second, explicit step inside a `seal`-toned panel, not a single click that
            // fires the request immediately.
            <div role="alertdialog" aria-label="Confirm withdrawal" className="rounded-[3px] border border-seal/30 bg-seal/[0.05] p-5">
              <p className="font-serif text-base font-semibold text-seal">Withdraw this submission?</p>
              <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-ink/70">
                This cannot be undone. Editors and reviewers will no longer be able to act on this
                manuscript, and you will need to submit again from scratch to be reconsidered.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button variant="danger" isLoading={withdrawing} onClick={withdraw}>
                  {withdrawing ? "Withdrawing…" : "Yes, withdraw it"}
                </Button>
                <Button variant="secondary" disabled={withdrawing} onClick={() => setConfirmingWithdraw(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
      {/*
        No status history: Plan 4 exposes no event/audit log endpoint. Re-add a timeline the
        day a `GET .../events` route exists to back it.
      */}
    </>
  );
}

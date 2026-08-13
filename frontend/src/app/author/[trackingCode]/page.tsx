"use client";
import { Suspense, use, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge, StatusExplanation } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { BackLink } from "@/components/ui/back-link";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { ResubmitForm } from "@/components/resubmit-form";
import { ApcPanel } from "@/components/apc-panel";
import type { Manuscript, ProblemDetails } from "@/types/api";

const WITHDRAWABLE = new Set(["submitted", "under_screening", "under_review", "reviews_complete", "revision_requested"]);
// An APC invoice can only exist once acceptance is on the record — earlier statuses have
// nothing to bill, so the panel (and its billing fetch) never appears before then.
const BILLABLE = new Set(["accepted", "scheduled", "published"]);

/** Isolated so `useSearchParams()` — which Next 15 requires to sit inside a Suspense
 * boundary during the build's static shell — doesn't force the whole detail page (and its
 * SWR-driven data) to wait behind that boundary too. */
function SubmittedBanner() {
  if (useSearchParams().get("submitted") !== "1") return null;
  return (
    <div className="mb-6 rounded-[3px] border-l-2 border-stamp bg-stamp/[0.06] px-4 py-3">
      <p className="font-medium text-ink">Manuscript received and accession-stamped.</p>
      <p className="mt-1 text-sm text-ink/70">
        What happens next: an editor will begin screening it, then either desk reject it or send it to two
        reviewers under double-blind conditions. You&apos;ll see its status update here as it moves — no separate
        notification is sent.
      </p>
    </div>
  );
}

export default function ManuscriptDetailPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);
  const [withdrawing, setWithdrawing] = useState(false);
  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false);
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
    mutate();
  }

  return (
    <>
      <BackLink href="/author" label="My submissions" />
      <Suspense fallback={null}>
        <SubmittedBanner />
      </Suspense>
      <div className="flex items-center justify-between">
        <h1 className="font-display-heading text-2xl font-semibold text-ink">{data.title}</h1>
        <StatusBadge status={data.status} />
      </div>
      <TrackingChip code={data.tracking_code} className="mt-1" />
      <StatusExplanation status={data.status} className="mt-2" />
      <p className="mt-4 leading-relaxed text-ink/80">{data.abstract}</p>
      <p className="mt-4 text-sm text-ink/60">{data.submitted_reviews} of {data.minimum_reviews} reviews submitted</p>

      {data.has_document && (
        <PdfViewer
          trackingCode={data.tracking_code}
          documentEndpoint={`/api/manuscripts/${trackingCode}/document`}
          title={data.title}
          variant="original"
          className="mt-4"
        />
      )}

      {BILLABLE.has(data.status) && (
        <div className="mt-6 border-t border-rule pt-6">
          <ApcPanel trackingCode={trackingCode} variant="author" />
        </div>
      )}

      {withdrawProblem && (
        <div className="mt-4">
          <ProblemAlert problem={withdrawProblem} />
        </div>
      )}
      {WITHDRAWABLE.has(data.status) && !confirmingWithdraw && (
        <Button variant="danger" className="mt-4" onClick={() => setConfirmingWithdraw(true)}>
          Withdraw submission
        </Button>
      )}
      {/* Withdrawal is terminal — the same two-step confirmation the editor's destructive
          decisions already require, not a single click on an irreversible action. */}
      {WITHDRAWABLE.has(data.status) && confirmingWithdraw && (
        <div className="mt-4 rounded-[3px] border-l-2 border-seal bg-seal/[0.05] px-4 py-3">
          <p className="text-sm font-medium text-ink">
            Withdrawing is permanent. The manuscript leaves the editorial process and cannot be
            reinstated — a new submission would receive a new tracking code.
          </p>
          <div className="mt-3 flex gap-3">
            <Button variant="danger" isLoading={withdrawing} onClick={withdraw}>
              {withdrawing ? "Withdrawing…" : "Confirm withdrawal"}
            </Button>
            <Button variant="secondary" disabled={withdrawing} onClick={() => setConfirmingWithdraw(false)}>
              Keep the submission
            </Button>
          </div>
        </div>
      )}
      {data.status === "revision_requested" && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-display-heading text-lg font-semibold text-ink">Resubmit a revised manuscript</h2>
          <ResubmitForm trackingCode={trackingCode} onResubmitted={mutate} />
        </div>
      )}
      {/*
        No status history: Plan 4 exposes no event/audit log endpoint. Re-add a timeline the
        day a `GET .../events` route exists to back it.
      */}
    </>
  );
}

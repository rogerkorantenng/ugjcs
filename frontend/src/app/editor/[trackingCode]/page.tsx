"use client";
import { use } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { ReviewerAssignForm } from "@/components/reviewer-assign-form";
import { DecisionForm } from "@/components/decision-form";
import type { Manuscript } from "@/types/api";

export default function EditorialManuscriptPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);

  if (isLoading) return <p>Loading…</p>;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  if (!data) return null;

  async function screen() {
    await fetch(`/api/editorial/${trackingCode}/screen`, { method: "POST" });
    mutate();
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl font-semibold text-ink">{data.title}</h1>
        <StatusBadge status={data.status} />
      </div>
      <TrackingChip code={data.tracking_code} className="mt-1" />
      <p className="mt-4 leading-relaxed text-ink/80">{data.abstract}</p>
      <p className="mt-4 text-sm text-ink/60">{data.submitted_reviews} of {data.minimum_reviews} reviews submitted</p>

      {data.status === "submitted" && (
        <div className="mt-6 border-t border-rule pt-6">
          <button
            onClick={screen}
            className="rounded-[3px] bg-teal px-4 py-2 text-sm font-medium text-paper hover:bg-teal-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
          >
            Begin screening
          </button>
        </div>
      )}

      {data.status === "under_screening" && (
        <div className="mt-6 border-t border-rule pt-6">
          <h2 className="font-serif text-lg font-semibold text-ink">Assign a reviewer</h2>
          <ReviewerAssignForm trackingCode={trackingCode} onAssigned={mutate} />
        </div>
      )}

      <div className="mt-6 border-t border-rule pt-6">
        <h2 className="font-serif text-lg font-semibold text-ink">Decision</h2>
        <DecisionForm trackingCode={trackingCode} status={data.status} onDecided={mutate} />
      </div>
    </>
  );
}

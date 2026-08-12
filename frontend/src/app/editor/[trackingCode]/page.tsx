"use client";
import { use, useState } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { ManuscriptDetailSkeleton } from "@/components/skeletons";
import { ReviewerAssignForm } from "@/components/reviewer-assign-form";
import { DecisionForm } from "@/components/decision-form";
import type { Manuscript, ProblemDetails } from "@/types/api";

export default function EditorialManuscriptPage({ params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = use(params);
  const { data, error, isLoading, mutate } = useApi<Manuscript>(`/api/manuscripts/${trackingCode}`);
  const [screening, setScreening] = useState(false);
  const [screenProblem, setScreenProblem] = useState<ProblemDetails | null>(null);

  if (isLoading) return <ManuscriptDetailSkeleton label="Loading manuscript…" />;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );
  if (!data) return null;

  async function screen() {
    setScreening(true);
    setScreenProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/screen`, { method: "POST" });
    setScreening(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setScreenProblem(detail ?? { type: "about:blank", title: "Could not begin screening", status: response.status });
      return;
    }
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
          {screenProblem && (
            <div className="mb-4">
              <ProblemAlert problem={screenProblem} />
            </div>
          )}
          <Button isLoading={screening} onClick={screen}>{screening ? "Starting…" : "Begin screening"}</Button>
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

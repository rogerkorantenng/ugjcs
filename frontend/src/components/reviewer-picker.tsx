"use client";
import { useState, type FormEvent } from "react";
import { useApi, ClientApiError } from "@/lib/use-api";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import type { ProblemDetails, ReviewerCandidate } from "@/types/api";

/**
 * Replaces the old "reviewer account id" free-text field. Lists every candidate `GET
 * /editorial/{trackingCode}/reviewer-candidates` returns, with their affiliation and
 * current load — and renders an excluded candidate greyed out with its reason *visible*,
 * never simply omitted. An editor seeing why someone can't review is the
 * conflict-of-interest check surfacing at the point of decision, not a hidden guard.
 */
export function ReviewerPicker({ trackingCode, onAssigned }: { trackingCode: string; onAssigned: () => void }) {
  const { data, error, isLoading } = useApi<ReviewerCandidate[]>(`/api/editorial/${trackingCode}/reviewer-candidates`);
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  if (isLoading) return <p className="mt-3 text-sm text-ink/60">Loading candidates…</p>;
  if (error) {
    return (
      <div className="mt-3">
        <ProblemAlert
          problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Could not load reviewer candidates", status: 500 }}
        />
      </div>
    );
  }
  if (!data || data.length === 0) {
    return <EmptyState title="No reviewer candidates found" hint="There are no registered reviewer accounts to assign yet." />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/reviewers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer_id: selected }),
    });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not assign that reviewer", status: response.status });
      return;
    }
    setSelected(null);
    onAssigned();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4" aria-label="Assign reviewer" aria-busy={submitting}>
      {problem && (
        <div className="mb-3">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <fieldset className="space-y-2">
        <legend className="sr-only">Choose a reviewer</legend>
        {data.map((candidate) => {
          const excluded = candidate.excluded_reason !== null;
          const atCapacity = candidate.active_assignments >= candidate.reviewer_capacity;
          return (
            <label
              key={candidate.id}
              className={`flex cursor-pointer items-start gap-3 rounded-[3px] border px-3 py-2.5 text-sm transition-colors
                ${excluded ? "cursor-not-allowed border-rule bg-ink/[0.02] opacity-60" : "border-rule bg-surface hover:border-stamp/40"}
                ${selected === candidate.id ? "border-stamp bg-stamp/[0.05]" : ""}`}
            >
              <input
                type="radio"
                name="reviewer_id"
                value={candidate.id}
                disabled={excluded}
                checked={selected === candidate.id}
                onChange={() => setSelected(candidate.id)}
                className="mt-0.5 accent-stamp"
              />
              <span className="flex-1">
                <span className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="font-medium text-ink">{candidate.full_name}</span>
                  <span className={`font-mono text-xs ${atCapacity && !excluded ? "text-seal" : "text-ink/50"}`}>
                    {candidate.active_assignments}/{candidate.reviewer_capacity} assigned
                  </span>
                </span>
                <span className="block text-ink/60">{candidate.affiliation}</span>
                {excluded && <span className="mt-0.5 block text-xs font-medium text-seal">Excluded — {candidate.excluded_reason}</span>}
              </span>
            </label>
          );
        })}
      </fieldset>
      <Button type="submit" isLoading={submitting} disabled={!selected} className="mt-4">
        {submitting ? "Assigning…" : "Assign selected reviewer"}
      </Button>
    </form>
  );
}

"use client";
import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { ProblemDetails } from "@/types/api";

/**
 * A raw reviewer-id input, not a `<select>` of candidates: Plan 4 has no
 * `GET /editorial/reviewer-candidates` endpoint at all (docs/05-api-contract.md §6) —
 * reviewer assignment is a persistence-only record with no scoring, no conflict-of-
 * interest exclusion check, and no candidate-listing endpoint to populate a picker from.
 * An editor must already know the reviewer's account id. Tracked as a technical-debt gap.
 */
export function ReviewerAssignForm({ trackingCode, onAssigned }: { trackingCode: string; onAssigned: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/reviewers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer_id: form.get("reviewer_id") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(
        detail ?? {
          type: "about:blank",
          title: "Could not assign that reviewer",
          status: response.status,
          detail: "Check the account id and try again.",
        },
      );
      return;
    }
    formElement.reset();
    onAssigned();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-wrap items-end gap-3" aria-label="Assign reviewer" aria-busy={submitting}>
      {problem && (
        <div className="w-full">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <div className="min-w-64 flex-1">
        <Input label="Reviewer account id" name="reviewer_id" required />
      </div>
      <Button type="submit" isLoading={submitting}>{submitting ? "Assigning…" : "Assign"}</Button>
    </form>
  );
}

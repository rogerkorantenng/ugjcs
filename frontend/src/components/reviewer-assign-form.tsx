"use client";
import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

/**
 * A raw reviewer-id input, not a `<select>` of candidates: Plan 4 has no
 * `GET /editorial/reviewer-candidates` endpoint at all (docs/05-api-contract.md §6) —
 * reviewer assignment is a persistence-only record with no scoring, no conflict-of-
 * interest exclusion check, and no candidate-listing endpoint to populate a picker from.
 * An editor must already know the reviewer's account id. Tracked as a technical-debt gap.
 */
export function ReviewerAssignForm({ trackingCode, onAssigned }: { trackingCode: string; onAssigned: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setSubmitting(true);
    setErrorMessage(null);
    const response = await fetch(`/api/editorial/${trackingCode}/reviewers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer_id: form.get("reviewer_id") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setErrorMessage("Could not assign that reviewer. Check the account id and try again.");
      return;
    }
    formElement.reset();
    onAssigned();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-wrap items-end gap-3" aria-label="Assign reviewer">
      {errorMessage && <p role="alert" className="w-full text-sm text-brick">{errorMessage}</p>}
      <div className="min-w-64 flex-1">
        <Input label="Reviewer account id" name="reviewer_id" required />
      </div>
      <Button type="submit" disabled={submitting}>{submitting ? "Assigning…" : "Assign"}</Button>
    </form>
  );
}

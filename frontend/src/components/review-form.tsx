"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RECOMMENDATIONS, type Recommendation } from "@/types/api";

/**
 * `SubmitReviewRequest` is `{recommendation, comments}` — one free-text recommendation
 * string, one free-text comments string (docs/05-api-contract.md §6/§7). No per-criterion
 * scores object and no `comments_to_author`/`confidential_comments_to_editor` split exist
 * on the backend.
 */
export function ReviewForm({ trackingCode, onSubmitted }: { trackingCode: string; onSubmitted: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setErrorMessage(null);
    const response = await fetch(`/api/reviews/${trackingCode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recommendation: form.get("recommendation") as Recommendation,
        comments: form.get("comments"),
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setErrorMessage("Could not submit the review. Please try again.");
      return;
    }
    onSubmitted();
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-4" aria-label="Submit review">
      {errorMessage && <p role="alert" className="text-brick">{errorMessage}</p>}
      <Select label="Recommendation" name="recommendation" required>
        {RECOMMENDATIONS.map((value) => (
          <option key={value} value={value}>{value.replace("_", " ")}</option>
        ))}
      </Select>
      <Textarea label="Comments" name="comments" required minLength={20} />
      <Button type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit review"}</Button>
    </form>
  );
}

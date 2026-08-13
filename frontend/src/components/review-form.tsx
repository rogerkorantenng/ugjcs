"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { RECOMMENDATIONS, SCORES, type Recommendation, type ProblemDetails } from "@/types/api";

/**
 * FR-11's structured review: four 1-5 criterion scores (originality, rigour, clarity,
 * significance), an overall recommendation, comments meant for the author, and
 * confidential comments meant for the editor alone — mirrors `SubmitReviewRequest`
 * (`backend/src/ugjcs/api/schemas.py`). `confidential_comments_to_editor` is read only
 * by `GET /editorial/{trackingCode}/reviews`, a route no author-facing page ever calls.
 */
export function ReviewForm({ trackingCode, onSubmitted }: { trackingCode: string; onSubmitted: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/reviews/${trackingCode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recommendation: form.get("recommendation") as Recommendation,
        originality_score: Number(form.get("originality_score")),
        rigour_score: Number(form.get("rigour_score")),
        clarity_score: Number(form.get("clarity_score")),
        significance_score: Number(form.get("significance_score")),
        comments_to_author: form.get("comments_to_author"),
        confidential_comments_to_editor: form.get("confidential_comments_to_editor"),
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not submit the review", status: response.status });
      return;
    }
    onSubmitted();
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-4" aria-label="Submit review" aria-busy={submitting}>
      {problem && <ProblemAlert problem={problem} />}
      <div className="grid gap-4 sm:grid-cols-2">
        <ScoreSelect name="originality_score" label="Originality" />
        <ScoreSelect name="rigour_score" label="Rigour" />
        <ScoreSelect name="clarity_score" label="Clarity" />
        <ScoreSelect name="significance_score" label="Significance" />
      </div>
      <Select label="Recommendation" name="recommendation" required>
        {RECOMMENDATIONS.map((value) => (
          <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
        ))}
      </Select>
      <Textarea
        label="Comments to the author"
        name="comments_to_author"
        required
        minLength={20}
        hint="At least 20 characters. The author will read this once a decision is recorded."
      />
      <Textarea
        label="Confidential comments to the editor"
        name="confidential_comments_to_editor"
        required
        minLength={10}
        hint="At least 10 characters. Seen only by the handling editor — the author never sees this field."
      />
      <Button type="submit" isLoading={submitting}>{submitting ? "Submitting…" : "Submit review"}</Button>
    </form>
  );
}

function ScoreSelect({ name, label }: { name: string; label: string }) {
  return (
    <Select label={`${label} (1–5)`} name={name} required defaultValue="">
      <option value="" disabled>Choose a score</option>
      {SCORES.map((score) => (
        <option key={score} value={score}>{score}</option>
      ))}
    </Select>
  );
}

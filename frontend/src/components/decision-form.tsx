"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { DecisionType, ManuscriptStatus, ProblemDetails } from "@/types/api";

// A UX hint mirroring the manuscript lifecycle guards (design spec §6.2), not a security
// control — the backend re-validates every transition regardless of what this component
// allows the editor to pick.
const AVAILABLE_BY_STATUS: Record<ManuscriptStatus, DecisionType[]> = {
  draft: [], submitted: [],
  under_screening: ["desk_reject", "send_to_review"],
  desk_rejected: [], under_review: [],
  reviews_complete: ["request_revision", "accept", "reject"],
  // Legal per `domain/transitions.py`: RESUBMITTED -> UNDER_REVIEW directly, without a
  // second screening pass — an editor may send a resubmission straight back to review.
  revision_requested: [], resubmitted: ["send_to_review"],
  accepted: [], rejected: [], scheduled: [], published: [], withdrawn: [],
};

/** Whether `DecisionForm` would render anything for this status — the caller
 * (`editor/[trackingCode]/page.tsx`) uses this to decide whether to render the "Decision"
 * section heading at all, so a terminal-state manuscript doesn't show an empty heading
 * over nothing. */
export function hasAvailableDecision(status: ManuscriptStatus): boolean {
  return AVAILABLE_BY_STATUS[status].length > 0;
}

export function DecisionForm({ trackingCode, status, onDecided }: { trackingCode: string; status: ManuscriptStatus; onDecided: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const available = AVAILABLE_BY_STATUS[status];
  if (available.length === 0) return null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: form.get("decision"), rationale: form.get("rationale") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not record the decision", status: response.status });
      return;
    }
    onDecided();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 space-y-4" aria-label="Record decision" aria-busy={submitting}>
      {problem && <ProblemAlert problem={problem} />}
      <Select label="Decision" name="decision" required>
        {available.map((decision) => (
          <option key={decision} value={decision}>{decision.replaceAll("_", " ")}</option>
        ))}
      </Select>
      <Textarea label="Rationale" name="rationale" required minLength={20} />
      <Button type="submit" isLoading={submitting}>{submitting ? "Recording…" : "Record decision"}</Button>
    </form>
  );
}

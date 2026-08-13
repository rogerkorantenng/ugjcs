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

// A decision that ends a manuscript's chances is rendered with the `danger` button —
// "destructive actions should look different from routine ones" — a `send_to_review` or
// `request_revision` stays the routine `primary` look.
const IRREVERSIBLE: Set<DecisionType> = new Set(["desk_reject", "reject"]);

// Decisions that cannot be walked back once recorded take two clicks: the first arms the
// form, the second — relabelled "Confirm …" beside a "Go back" escape — records it. This
// is the same arm-then-confirm shape as withdrawing a submission or waiving an APC.
// `accept` belongs here too: it issues the APC invoice and commits the manuscript to the
// publication path, even though it isn't rendered as a danger.
const CONFIRM_REQUIRED: Set<DecisionType> = new Set(["desk_reject", "reject", "accept"]);

/** Whether `DecisionForm` would render anything for this status — the caller
 * (`editor/[trackingCode]/page.tsx`) uses this to decide whether to render the "Decision"
 * section heading at all, so a terminal-state manuscript doesn't show an empty heading
 * over nothing. */
export function hasAvailableDecision(status: ManuscriptStatus): boolean {
  return AVAILABLE_BY_STATUS[status].length > 0;
}

export function DecisionForm({ trackingCode, status, onDecided }: { trackingCode: string; status: ManuscriptStatus; onDecided: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [armed, setArmed] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const available = AVAILABLE_BY_STATUS[status];
  const [decision, setDecision] = useState<DecisionType | "">(available[0] ?? "");
  if (available.length === 0) return null;
  const isDestructive = IRREVERSIBLE.has(decision as DecisionType);
  const needsConfirm = CONFIRM_REQUIRED.has(decision as DecisionType);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (needsConfirm && !armed) {
      // First click only arms the form — the browser has already run its validity
      // checks by the time submit fires, so a half-filled form never reaches here.
      setArmed(true);
      return;
    }
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
      <Select
        label="Decision"
        name="decision"
        required
        value={decision}
        onChange={(event) => {
          setDecision(event.target.value as DecisionType);
          setArmed(false);
        }}
      >
        {available.map((value) => (
          <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
        ))}
      </Select>
      <Textarea
        label="Rationale"
        name="rationale"
        required
        minLength={20}
        hint="At least 20 characters — this is recorded against the manuscript's record."
      />
      {armed && (
        <p className="text-sm text-seal">
          {isDestructive
            ? "This decision ends this manuscript's path through review and cannot be undone."
            : "A recorded decision is final and cannot be edited afterwards."}
        </p>
      )}
      <div className="flex items-center gap-3">
        <Button type="submit" variant={isDestructive ? "danger" : "primary"} isLoading={submitting}>
          {submitting
            ? "Recording…"
            : armed
              ? `Confirm ${decision.replaceAll("_", " ")}`
              : "Record decision"}
        </Button>
        {armed && !submitting && (
          <Button type="button" variant="secondary" onClick={() => setArmed(false)}>
            Go back
          </Button>
        )}
      </div>
    </form>
  );
}

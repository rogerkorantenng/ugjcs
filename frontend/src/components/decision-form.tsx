"use client";
import { useState, type FormEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { DecisionType, ManuscriptStatus } from "@/types/api";

// A UX hint mirroring the manuscript lifecycle guards (design spec §6.2), not a security
// control — the backend re-validates every transition regardless of what this component
// allows the editor to pick.
const AVAILABLE_BY_STATUS: Record<ManuscriptStatus, DecisionType[]> = {
  draft: [], submitted: [],
  under_screening: ["desk_reject", "send_to_review"],
  desk_rejected: [], under_review: [],
  reviews_complete: ["request_revision", "accept", "reject"],
  revision_requested: [], resubmitted: [], accepted: [], rejected: [], scheduled: [], published: [], withdrawn: [],
};

export function DecisionForm({ trackingCode, status, onDecided }: { trackingCode: string; status: ManuscriptStatus; onDecided: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const available = AVAILABLE_BY_STATUS[status];
  if (available.length === 0) return null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    await fetch(`/api/editorial/${trackingCode}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: form.get("decision"), rationale: form.get("rationale") }),
    });
    setSubmitting(false);
    onDecided();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 space-y-4" aria-label="Record decision">
      <Select label="Decision" name="decision" required>
        {available.map((decision) => (
          <option key={decision} value={decision}>{decision.replace("_", " ")}</option>
        ))}
      </Select>
      <Textarea label="Rationale" name="rationale" required minLength={20} />
      <Button type="submit" disabled={submitting}>{submitting ? "Recording…" : "Record decision"}</Button>
    </form>
  );
}

"use client";
import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import type { ManuscriptStatus, ProblemDetails } from "@/types/api";

/**
 * `Action.PUBLISH` (`backend/src/ugjcs/domain/policies.py`) is granted to the
 * Editor-in-Chief alone, and it gates both moves below — scheduling (`accepted` ->
 * `scheduled`) and publishing (`scheduled` -> `published`), per
 * `backend/src/ugjcs/domain/transitions.py`. The caller (`editor/[trackingCode]/page.tsx`)
 * is responsible for rendering this only when the signed-in actor holds that role and the
 * manuscript is in one of these two states; the backend enforces both regardless, this is
 * UI tidiness, not the security boundary.
 */
export function PublicationPanel({
  trackingCode,
  status,
  onChanged,
}: {
  trackingCode: string;
  status: ManuscriptStatus;
  onChanged: () => void;
}) {
  if (status === "accepted") return <ScheduleForm trackingCode={trackingCode} onScheduled={onChanged} />;
  if (status === "scheduled") return <PublishButton trackingCode={trackingCode} onPublished={onChanged} />;
  return null;
}

function ScheduleForm({ trackingCode, onScheduled }: { trackingCode: string; onScheduled: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ volume: Number(form.get("volume")), number: Number(form.get("number")) }),
    });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not schedule the manuscript", status: response.status });
      return;
    }
    onScheduled();
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-wrap items-end gap-3" aria-label="Schedule into an issue" aria-busy={submitting}>
      {problem && (
        <div className="w-full">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <div className="w-28">
        <Input label="Volume" name="volume" type="number" min={1} required />
      </div>
      <div className="w-28">
        <Input label="Number" name="number" type="number" min={1} required />
      </div>
      <Button type="submit" isLoading={submitting}>
        {submitting ? "Scheduling…" : "Schedule"}
      </Button>
    </form>
  );
}

function PublishButton({ trackingCode, onPublished }: { trackingCode: string; onPublished: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  async function publish() {
    setSubmitting(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/publish`, { method: "POST" });
    setSubmitting(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not publish the manuscript", status: response.status });
      return;
    }
    onPublished();
  }

  return (
    <div className="mt-4">
      {problem && (
        <div className="mb-3">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <Button isLoading={submitting} onClick={publish}>
        {submitting ? "Publishing…" : "Publish"}
      </Button>
    </div>
  );
}

"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ProblemAlert } from "@/components/ui/alert";
import { SCREENABLE_STATUSES } from "@/lib/editorial-statuses";
import type { ManuscriptStatus, ProblemDetails } from "@/types/api";

/**
 * The editor's "Begin screening" action, extracted whole from the detail page. No request
 * body — `POST /editorial/{trackingCode}/screen` moves `submitted` (or `resubmitted`) to
 * `under_screening`. Renders nothing from any other status.
 */
export function ScreenControl({
  trackingCode,
  status,
  onScreened,
}: {
  trackingCode: string;
  status: ManuscriptStatus;
  onScreened: () => void;
}) {
  const [screening, setScreening] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  if (!SCREENABLE_STATUSES.has(status)) return null;

  async function screen() {
    setScreening(true);
    setProblem(null);
    const response = await fetch(`/api/editorial/${trackingCode}/screen`, { method: "POST" });
    setScreening(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      setProblem(detail ?? { type: "about:blank", title: "Could not begin screening", status: response.status });
      return;
    }
    onScreened();
  }

  return (
    <div className="mt-6 border-t border-rule pt-6">
      {problem && (
        <div className="mb-4">
          <ProblemAlert problem={problem} />
        </div>
      )}
      <Button isLoading={screening} onClick={screen}>{screening ? "Starting…" : "Begin screening"}</Button>
    </div>
  );
}

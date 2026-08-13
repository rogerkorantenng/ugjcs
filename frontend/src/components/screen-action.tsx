"use client";
import { useState } from "react";
import { ProblemAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ProblemDetails } from "@/types/api";

/**
 * The "Begin screening" action block on the editor's manuscript page — owns its own
 * in-flight and problem state so the page itself stays a layout of sections.
 * `POST /api/editorial/{trackingCode}/screen`, then hands control back via `onScreened`
 * (the page revalidates the manuscript).
 */
export function ScreenAction({ trackingCode, onScreened }: { trackingCode: string; onScreened: () => void }) {
  const [screening, setScreening] = useState(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

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

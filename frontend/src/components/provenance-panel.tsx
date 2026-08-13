"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { ProblemDetails } from "@/types/api";
import type { ProvenanceOut } from "@/types/scholarly";

/** `a1b2…9f0e` — enough of both ends of the digest to compare against an independent
 * record, without a 64-hex-character line wrecking the layout on a phone. The full hash
 * rides along in `title` for anyone who hovers or copies. */
function truncateMiddle(hash: string): string {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 10)}…${hash.slice(-8)}`;
}

function formatOccurredAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/**
 * The interactive half of the "Editorial provenance" section on a public paper page.
 * Nothing fetches until the reader clicks "Verify chain" — the verdict is the backend
 * re-hashing the event chain live at click time (the BFF route is `no-store` for the
 * same reason), so an idle page costs the archive nothing.
 */
export function ProvenancePanel({ trackingCode }: { trackingCode: string }) {
  const [provenance, setProvenance] = useState<ProvenanceOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  async function verify() {
    setVerifying(true);
    setError(null);
    try {
      const response = await fetch(`/api/archive/${trackingCode}/provenance`);
      if (!response.ok) {
        const problem = (await response.json().catch(() => null)) as ProblemDetails | null;
        setError(problem?.title ?? "Could not verify the chain");
        return;
      }
      setProvenance((await response.json()) as ProvenanceOut);
    } catch {
      setError("Could not reach the server");
    } finally {
      setVerifying(false);
    }
  }

  if (error) {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 border-l-2 border-seal bg-seal/5 px-4 py-3">
        <span aria-hidden="true" className="text-seal">⚠</span>
        <p className="font-semibold text-seal">{error}</p>
        <Button variant="secondary" onClick={verify} isLoading={verifying}>
          Try again
        </Button>
      </div>
    );
  }

  if (!provenance) {
    return (
      <Button variant="secondary" onClick={verify} isLoading={verifying}>
        {verifying ? "Verifying…" : "Verify chain"}
      </Button>
    );
  }

  return (
    <div>
      {provenance.intact ? (
        <p className="font-mono text-sm font-semibold uppercase tracking-[0.14em] text-verified">Chain intact ✓</p>
      ) : (
        <p className="font-mono text-sm font-semibold uppercase tracking-[0.14em] text-seal">CHAIN BROKEN</p>
      )}
      <p className="mt-2 text-sm text-ink/70">
        Head hash{" "}
        <span className="font-mono text-xs text-ink" title={provenance.head_hash}>
          {truncateMiddle(provenance.head_hash)}
        </span>
      </p>
      <ol className="mt-4 space-y-1.5 border-l border-rule pl-4">
        {provenance.events.map((event) => (
          <li key={event.sequence} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-sm">
            <span className="font-mono text-xs text-stamp">{String(event.sequence).padStart(2, "0")}</span>
            <span className="text-ink">{event.event_type.replaceAll("_", " ")}</span>
            <span className="text-xs text-ink/50">{formatOccurredAt(event.occurred_at)}</span>
            <span className="font-mono text-xs text-ink/40">{event.hash_prefix}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-xs text-ink/50">
        Verification proves recorded history is internally consistent — it cannot prove events were never removed
        from the tail.
      </p>
    </div>
  );
}

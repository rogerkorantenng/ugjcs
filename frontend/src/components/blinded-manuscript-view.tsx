import { TrackingChip } from "@/components/ui/tracking-chip";
import { StatusBadge, StatusExplanation } from "@/components/ui/badge";
import { RedactedAuthorSlot } from "@/components/ui/redaction-bar";
import type { BlindedManuscript } from "@/types/api";

/**
 * Renders exactly the fields on `BlindedManuscript` — a type with no author field to leak,
 * and (per docs/05-api-contract.md's reconciled shape) no `id` and no `document_url`
 * either: Plan 4 stores no document of any kind. Do not widen this component's prop type
 * to `Manuscript` or anything with an author field "just to reuse it": the type boundary
 * here is the control, not a formality. `RedactedAuthorSlot` below takes no name prop at
 * all — the signature device this app uses to make that boundary visible, not just enforced
 * silently.
 */
export function BlindedManuscriptView({ manuscript }: { manuscript: BlindedManuscript }) {
  return (
    <article>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TrackingChip code={manuscript.tracking_code} />
        <StatusBadge status={manuscript.status} />
      </div>
      <h1 className="font-display-heading mt-2 text-2xl font-semibold text-ink">{manuscript.title}</h1>
      <StatusExplanation status={manuscript.status} className="mt-1" />
      <RedactedAuthorSlot className="mt-4" />
      <p className="mt-4 leading-relaxed text-ink/80">{manuscript.abstract}</p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {manuscript.keywords.map((keyword) => (
          <li key={keyword} className="rounded-full border border-rule px-2.5 py-0.5 text-xs text-ink/70">
            {keyword}
          </li>
        ))}
      </ul>
    </article>
  );
}

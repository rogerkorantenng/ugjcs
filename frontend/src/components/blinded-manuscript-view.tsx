import { TrackingChip } from "@/components/ui/tracking-chip";
import { RedactionBar } from "@/components/ui/redaction-bar";
import type { BlindedManuscript } from "@/types/api";

/**
 * Renders exactly the fields on `BlindedManuscript` — a type with no author field to leak,
 * and (per docs/05-api-contract.md's reconciled shape) no `id` and no `document_url`
 * either: Plan 4 stores no document of any kind. Do not widen this component's prop type
 * to `Manuscript` or anything with an author field "just to reuse it": the type boundary
 * here is the control, not a formality. `RedactionBar` is rendered with no `names` prop for
 * exactly that reason — there is nothing on this type it could reveal even by mistake.
 */
export function BlindedManuscriptView({ manuscript }: { manuscript: BlindedManuscript }) {
  return (
    <article>
      <div className="flex flex-wrap items-center gap-2">
        <TrackingChip code={manuscript.tracking_code} />
        <RedactionBar />
      </div>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink">{manuscript.title}</h1>
      <p className="mt-4 leading-relaxed text-ink/80">{manuscript.abstract}</p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {manuscript.keywords.map((keyword) => (
          <li key={keyword} className="rounded-full border border-rule px-2.5 py-0.5 text-xs text-ink/70">
            {keyword}
          </li>
        ))}
      </ul>
      {/*
        No "Open manuscript" link: Plan 4 stores no document of any kind — no `document_url`
        field exists on `BlindedManuscript` (docs/05-api-contract.md §7). Re-add once a
        document-storage capability exists.
      */}
    </article>
  );
}

import Link from "next/link";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { RedactionBar } from "@/components/ui/redaction-bar";
import type { ArchivePaperOut } from "@/types/api";

/**
 * A quiet index row, not a boxed card — a journal's table of contents lists papers one
 * after another under hairlines; it does not put each one in its own tile with a shadow.
 * Shared by the homepage's numbered contents list (pass `index`) and the search results
 * list (omit it). The byline renders through `RedactionBar` with real names — the exact
 * shape a reviewer sees redacted, opened up, so the two screens visibly rhyme.
 */
export function PaperCard({ paper, index }: { paper: ArchivePaperOut; index?: number }) {
  return (
    <Link
      href={`/papers/${paper.tracking_code}`}
      className="group flex gap-4 border-t border-rule py-5 first:border-t-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp"
    >
      {index !== undefined && (
        <span
          aria-hidden="true"
          className="w-9 shrink-0 pt-0.5 font-serif text-2xl font-semibold tabular-nums leading-none text-ink/25 transition-colors group-hover:text-stamp sm:w-11 sm:text-3xl"
        >
          {String(index).padStart(2, "0")}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <h3 className="font-serif text-lg font-semibold leading-snug text-ink group-hover:text-stamp-dark">
          {paper.title}
        </h3>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <TrackingChip code={paper.tracking_code} />
          <RedactionBar names={paper.author_names} compact />
        </div>
        <p className="mt-2 line-clamp-2 max-w-2xl text-sm leading-relaxed text-ink/65">{paper.abstract}</p>
        {paper.keywords.length > 0 && (
          <ul className="mt-2.5 flex flex-wrap gap-1.5">
            {paper.keywords.slice(0, 4).map((keyword) => (
              <li
                key={keyword}
                className="rounded-full border border-rule px-2 py-0.5 text-[11px] uppercase tracking-wide text-ink/45"
              >
                {keyword}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Link>
  );
}

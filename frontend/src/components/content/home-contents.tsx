import Link from "next/link";
import { formatAuthors } from "@/lib/format";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import type { ArchivePaperOut } from "@/types/api";

/**
 * The contents page: a numbered list, the way a print issue's table of contents orders its
 * articles — not a card grid. Numbering is legitimate here: these papers have a real order
 * (most recently published first), not a decorative one.
 */
export function HomeContents({ papers }: { papers: ArchivePaperOut[] }) {
  return (
    <section className="mx-auto max-w-5xl px-4 py-14">
      <div className="flex items-baseline justify-between border-b-2 border-stamp pb-3">
        <h2 className="font-display-heading text-lg font-semibold text-ink">Contents</h2>
        <Link href="/search" className="text-sm font-medium text-stamp hover:text-stamp-dark">
          Browse all →
        </Link>
      </div>
      {papers.length > 0 ? (
        <ol className="divide-y divide-rule">
          {papers.map((paper, index) => (
            <li key={paper.tracking_code} className="group grid grid-cols-[3rem_1fr] gap-4 py-6 sm:grid-cols-[4rem_1fr]">
              <span
                aria-hidden="true"
                className="font-mono text-2xl font-light leading-none text-stamp/50 tabular-nums sm:text-3xl"
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0">
                <Link href={`/papers/${paper.tracking_code}`} className="rounded-[2px] focus-visible:outline-2 focus-visible:outline-offset-2">
                  <h3 className="font-display-heading text-lg font-semibold text-ink group-hover:text-stamp sm:text-xl">
                    {paper.title}
                  </h3>
                </Link>
                <p className="mt-1 text-sm text-ink/60">{formatAuthors(paper.author_names)}</p>
                <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink/70">{paper.abstract}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <TrackingChip code={paper.tracking_code} />
                  {paper.keywords.slice(0, 3).map((keyword) => (
                    <span key={keyword} className="rounded-full border border-rule px-2 py-0.5 text-[11px] uppercase tracking-wide text-ink/50">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <EmptyState title="No papers have been published yet" hint="Check back soon — new issues appear here as they clear review." />
      )}
    </section>
  );
}

import Link from "next/link";
import { getPublishedPapers } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonClasses } from "@/components/ui/button";

export const revalidate = 300;

/** Real, derived facts only — never a placeholder number. `/archive` carries no
 * `published_at`/volume/DOI (docs/05-api-contract.md §7): there is no true "Vol. N No. N"
 * to print on the cover, so the cover states what the data actually supports — how many
 * papers are in the current issue and how many distinct bylines stand behind them —
 * instead of inventing a volume/issue number nothing on the wire backs up. */
function issueFacts(papers: { author_names: string[] }[]) {
  const authors = new Set(papers.flatMap((paper) => paper.author_names));
  return { count: papers.length, authors: authors.size };
}

export default async function HomePage() {
  const papers = await getPublishedPapers();
  const facts = issueFacts(papers);

  return (
    <main>
      {/* The issue cover. A rule under the masthead, then the current-issue line standing
          in for the volume/number a print cover would carry — honestly, since no volume or
          issue number exists anywhere on the wire; see `issueFacts`. Contents follow as a
          numbered list below, not a grid of equal cards: papers in an issue genuinely have
          an order, the way entries in a table of contents do. */}
      <section className="border-b border-rule">
        <div className="mx-auto max-w-5xl px-4 pb-10 pt-14 sm:pt-20">
          <div className="animate-rise-in">
            <div aria-hidden="true" className="h-px w-16 bg-stamp" />
            <p className="mt-4 font-mono text-xs uppercase tracking-[0.22em] text-stamp">Current issue</p>
            <h1 className="font-display-wonk mt-3 max-w-3xl font-serif text-display font-semibold text-ink sm:text-5xl">
              Rigorously reviewed computing research, from Legon and beyond.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-ink/65 sm:text-lg">
              Every manuscript is screened, reviewed twice under strict double-blind conditions,
              and decided on by an editor before it reaches this archive
              {facts.count > 0 ? (
                <>
                  {" — "}
                  {facts.count} {facts.count === 1 ? "paper" : "papers"} so far, from {facts.authors}{" "}
                  {facts.authors === 1 ? "author" : "authors"}.
                </>
              ) : (
                "."
              )}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-5">
              <Link href="/search" className={buttonClasses("primary")}>
                Search the archive
              </Link>
              <Link
                href="/login"
                className="text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp"
              >
                Sign in to submit a manuscript
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-12 sm:py-14">
        <div className="flex items-baseline justify-between gap-4 border-b border-rule pb-3">
          <h2 className="font-serif text-lg font-semibold text-ink">Contents</h2>
          <Link href="/search" className="text-sm font-medium text-stamp hover:text-stamp-dark">
            Browse all →
          </Link>
        </div>
        {papers.length > 0 ? (
          <div>
            {papers.slice(0, 8).map((paper, i) => (
              <PaperCard key={paper.tracking_code} paper={paper} index={i + 1} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No papers have been published yet"
            hint="Check back soon — new issues appear here as they clear review."
          />
        )}
      </section>
    </main>
  );
}

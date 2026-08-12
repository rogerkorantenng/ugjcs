import Link from "next/link";
import { getPublishedPapers } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonClasses } from "@/components/ui/button";

export const revalidate = 300;

/** Counts real, derived facts only — never a placeholder number. `/archive` carries no
 * `published_at`/volume/DOI (docs/05-api-contract.md §7), so the strip states what the
 * data actually supports: how many papers, and how many distinct bylines behind them. */
function journalStats(papers: { author_names: string[] }[]) {
  const authors = new Set(papers.flatMap((paper) => paper.author_names));
  return [
    { label: "Published papers", value: papers.length },
    { label: "Contributing authors", value: authors.size },
    { label: "Reviewers per manuscript", value: 2 },
  ];
}

export default async function HomePage() {
  const papers = await getPublishedPapers();
  const recent = papers.slice(0, 6);
  const stats = journalStats(papers);

  return (
    <main>
      <section className="border-b border-rule bg-white/40">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:py-20">
          <div className="animate-rise-in max-w-2xl">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-teal-dark">
              A double-blind peer-reviewed journal
            </p>
            <h1 className="mt-4 font-serif text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Rigorously reviewed computing research, from Legon and beyond.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink/70">
              <span className="float-left mr-2 mt-1 font-serif text-5xl font-semibold leading-none text-teal-dark">U</span>
              GJCS publishes original research in computing and information systems. Every
              manuscript is screened, reviewed twice under strict double-blind conditions, and
              decided on by an editor before it reaches this archive.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link href="/search" className={buttonClasses("primary")}>
                Search the archive
              </Link>
              <Link
                href="/login"
                className="text-sm font-medium text-teal-dark underline decoration-teal/40 underline-offset-4 hover:decoration-amber hover:text-amber"
              >
                Sign in to submit a manuscript
              </Link>
            </div>
          </div>
          <dl className="mt-14 grid grid-cols-1 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule sm:grid-cols-3">
            {stats.map((stat) => (
              <div key={stat.label} className="bg-paper px-6 py-5">
                <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink/50">{stat.label}</dt>
                <dd className="mt-1 font-serif text-3xl font-semibold text-ink">{stat.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14">
        <div className="flex items-baseline justify-between border-b border-rule pb-3">
          <h2 className="font-serif text-lg font-semibold text-ink">Recently published</h2>
          <Link href="/search" className="text-sm font-medium text-teal-dark hover:text-amber">
            Browse all →
          </Link>
        </div>
        {recent.length > 0 ? (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {recent.map((paper) => (
              <PaperCard key={paper.tracking_code} paper={paper} />
            ))}
          </div>
        ) : (
          <EmptyState title="No papers have been published yet" hint="Check back soon — new issues appear here as they clear review." />
        )}
      </section>
    </main>
  );
}

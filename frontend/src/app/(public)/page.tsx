import Link from "next/link";
import { getPublishedPapers } from "@/lib/archive";
import { buttonClasses } from "@/components/ui/button";
import { HomeContents } from "@/components/content/home-contents";
import { HowItWorks } from "@/components/content/home-how-it-works";

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
  const stats = journalStats(papers);

  return (
    <main>
      {/* The issue cover: a masthead moment, not a hero banner — the one place the display
          face is allowed its full character (`.font-display-cover`), and the one entrance
          animation in the app. Everything past this section is deliberately quiet. */}
      <section className="border-b border-rule bg-surface/40">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:py-20">
          <div className="animate-rise-in max-w-2xl">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-stamp">
              A double-blind peer-reviewed journal
            </p>
            <h1 className="font-display-cover mt-4 text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl">
              University of Ghana Journal of Computing Science
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink/70">
              Original research in computing and information systems, from Legon and beyond. Every manuscript is
              screened, reviewed twice under strict double-blind conditions, and decided on by an editor before it
              reaches this archive.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
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
          <dl className="mt-14 grid grid-cols-1 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule sm:grid-cols-3">
            {stats.map((stat) => (
              <div key={stat.label} className="bg-paper px-6 py-5">
                <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink/50">{stat.label}</dt>
                <dd className="font-display-heading mt-1 text-3xl font-semibold text-ink">{stat.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <HomeContents papers={papers} />
      <HowItWorks />
    </main>
  );
}

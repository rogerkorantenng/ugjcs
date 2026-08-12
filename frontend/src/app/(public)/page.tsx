import Link from "next/link";
import { getPublishedPapers } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";
import { EmptyState } from "@/components/ui/empty-state";

export const revalidate = 300;

export default async function HomePage() {
  const papers = await getPublishedPapers();
  const recent = papers.slice(0, 5);

  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-teal-dark">A double-blind peer-reviewed journal</p>
      <h1 className="mt-3 font-serif text-3xl font-semibold leading-tight text-ink">
        University of Ghana Journal of Computing Science
      </h1>
      <p className="mt-4 max-w-xl leading-relaxed text-ink/70">
        Original, rigorously reviewed research in computing and information systems from the
        University of Ghana and beyond.
      </p>
      <Link
        href="/search"
        className="mt-6 inline-flex items-center gap-1.5 border-b border-teal text-sm font-medium text-teal-dark hover:border-amber hover:text-amber focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
      >
        Search the archive <span aria-hidden="true">→</span>
      </Link>
      <section className="mt-14">
        <h2 className="border-b border-rule pb-2 font-serif text-lg font-semibold text-ink">Recently published</h2>
        {recent.length > 0 ? (
          <div className="mt-6 grid gap-4">
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

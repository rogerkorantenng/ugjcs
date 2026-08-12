import Link from "next/link";
import { getPublishedPapers } from "@/lib/archive";
import { PaperCard } from "@/components/manuscript-card";

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
      <Link
        href="/search"
        className="mt-6 inline-block border-b border-teal text-sm font-medium text-teal-dark hover:border-amber hover:text-amber focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
      >
        Search the archive
      </Link>
      {recent.length > 0 && (
        <section className="mt-14">
          <h2 className="border-b border-rule pb-2 font-serif text-lg font-semibold text-ink">Recently published</h2>
          <div className="mt-6 grid gap-4">
            {recent.map((paper) => (
              <PaperCard key={paper.tracking_code} paper={paper} />
            ))}
          </div>
        </section>
      )}
      {recent.length === 0 && (
        <p className="mt-14 border-t border-rule pt-8 text-sm text-ink/60">
          No papers have been published yet. Check back soon.
        </p>
      )}
    </main>
  );
}

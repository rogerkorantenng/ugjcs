import type { Metadata } from "next";
import { getPaper } from "@/lib/archive";
import { formatAuthors } from "@/lib/format";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { buttonClasses } from "@/components/ui/button";

interface Params { trackingCode: string }

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { trackingCode } = await params;
  const paper = await getPaper(trackingCode);
  return {
    title: paper.title,
    description: paper.abstract.slice(0, 160),
    openGraph: { title: paper.title, description: paper.abstract.slice(0, 160), type: "article" },
  };
}

export default async function PaperPage({ params }: { params: Promise<Params> }) {
  const { trackingCode } = await params;
  const paper = await getPaper(trackingCode);

  // No `datePublished`/`identifier` (DOI): Plan 4 mints no DOI and exposes no publication
  // timestamp anywhere on the wire. Both are entered in the technical debt register rather
  // than filled with a placeholder value a search engine would index as real.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ScholarlyArticle",
    headline: paper.title,
    author: paper.author_names.map((name) => ({ "@type": "Person", name })),
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      {/* Highwire Press tags for Google Scholar indexing */}
      <meta name="citation_title" content={paper.title} />
      {paper.author_names.map((name) => (
        <meta key={name} name="citation_author" content={name} />
      ))}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <TrackingChip code={paper.tracking_code} />
      <h1 className="mt-3 font-serif text-2xl font-semibold leading-tight text-ink">{paper.title}</h1>
      <p className="mt-2 text-sm text-ink/60">{formatAuthors(paper.author_names)}</p>
      {paper.keywords.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {paper.keywords.map((keyword) => (
            <li key={keyword} className="rounded-full border border-rule px-2.5 py-0.5 text-xs text-ink/70">
              {keyword}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-8 border-t border-rule pt-8 leading-relaxed text-ink/80">{paper.abstract}</p>
      {paper.has_document && (
        <a
          href={`/api/archive/${paper.tracking_code}/document`}
          className={buttonClasses("primary", "mt-8")}
        >
          Download PDF
        </a>
      )}
    </main>
  );
}

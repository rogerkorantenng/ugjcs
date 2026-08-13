import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPaper } from "@/lib/archive";
import { ProblemDetailsError } from "@/lib/backend";
import type { ScholarlyPaper } from "@/types/scholarly";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { BackLink } from "@/components/ui/back-link";
import { RevealedAuthorSlot } from "@/components/ui/redaction-bar";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { CitationRow, ProvenanceSection } from "@/components/paper-scholarly";

type Params = Promise<{ trackingCode: string }>;

export const revalidate = 300;

/** A 404 from the archive becomes Next's not-found page; anything else keeps throwing.
 * Without this, an unknown tracking code returned HTTP 200 and left the reader staring
 * at the loading skeleton forever. */
async function getPaperOr404(trackingCode: string): Promise<ScholarlyPaper> {
  try {
    return await getPaper(trackingCode);
  } catch (error) {
    if (error instanceof ProblemDetailsError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { trackingCode } = await params;
  const paper = await getPaperOr404(trackingCode);
  return {
    title: paper.title,
    description: paper.abstract.slice(0, 160),
    openGraph: { title: paper.title, description: paper.abstract.slice(0, 160), type: "article" },
  };
}

export default async function PaperPage({ params }: { params: Params }) {
  const { trackingCode } = await params;
  const paper = await getPaperOr404(trackingCode);

  // No `datePublished`: the wire still exposes no publication timestamp (technical debt
  // register). `identifier` is the minted DOI when the backend serialises one — the field
  // is optional so this page keeps working against the pre-DOI API.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ScholarlyArticle",
    headline: paper.title,
    author: paper.author_names.map((name) => ({ "@type": "Person", name })),
    ...(paper.doi ? { identifier: paper.doi } : {}),
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      {/* Highwire Press tags for Google Scholar indexing */}
      <meta name="citation_title" content={paper.title} />
      {paper.author_names.map((name) => (
        <meta key={name} name="citation_author" content={name} />
      ))}
      {paper.doi && <meta name="citation_doi" content={paper.doi} />}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <BackLink href="/" label="All papers" />
      <div>
        <TrackingChip code={paper.tracking_code} />
      </div>
      <h1 className="font-display-heading mt-3 text-2xl font-semibold leading-tight text-ink">{paper.title}</h1>
      {/* The public half of the redaction/reveal rhyme: the same slot shape a reviewer sees
          rendered as a solid ink block (`RedactedAuthorSlot`) shows the real byline here. */}
      <RevealedAuthorSlot names={paper.author_names} className="mt-3" />
      {paper.keywords.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {paper.keywords.map((keyword) => (
            <li key={keyword} className="rounded-full border border-rule px-2.5 py-0.5 text-xs text-ink/70">
              {keyword}
            </li>
          ))}
        </ul>
      )}
      <CitationRow paper={paper} />
      <p className="mt-8 border-t border-rule pt-8 leading-relaxed text-ink/80">{paper.abstract}</p>
      {paper.has_document && (
        <PdfViewer
          trackingCode={paper.tracking_code}
          documentEndpoint={`/api/archive/${paper.tracking_code}/document`}
          title={paper.title}
          variant="original"
          className="mt-8"
        />
      )}
      <ProvenanceSection trackingCode={paper.tracking_code} />
    </main>
  );
}

import { buttonClasses } from "@/components/ui/button";
import { ProvenancePanel } from "@/components/provenance-panel";
import type { ScholarlyPaper } from "@/types/scholarly";

/**
 * The scholarly line under a paper's byline/keywords: the minted DOI (omitted entirely
 * against a pre-DOI backend) and the "Cite this paper" row. The BibTeX/RIS buttons are
 * plain anchors to the public citation proxy — the `Content-Disposition` header there
 * makes them downloads, so no client JS is needed on this server component.
 */
export function CitationRow({ paper }: { paper: ScholarlyPaper }) {
  const citationHref = (format: "bibtex" | "ris") => `/api/archive/${paper.tracking_code}/citation?format=${format}`;
  return (
    <>
      {paper.doi && <p className="mt-4 font-mono text-xs tracking-wide text-ink/60">DOI {paper.doi}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-ink/50">
          Cite this paper
        </span>
        <a href={citationHref("bibtex")} className={buttonClasses("secondary", "px-3 py-1 text-xs")}>
          BibTeX
        </a>
        <a href={citationHref("ris")} className={buttonClasses("secondary", "px-3 py-1 text-xs")}>
          RIS
        </a>
      </div>
    </>
  );
}

/** The bordered "Editorial provenance" section — static frame around the interactive
 * `ProvenancePanel`, kept here so the paper page itself stays a thin server component. */
export function ProvenanceSection({ trackingCode }: { trackingCode: string }) {
  return (
    <section aria-labelledby="provenance-heading" className="mt-10 rounded-[3px] border border-rule bg-surface p-5">
      <h2 id="provenance-heading" className="font-display-heading text-lg font-semibold text-ink">
        Editorial provenance
      </h2>
      <p className="mt-1 text-sm text-ink/60">
        Every editorial action on this manuscript is hash-chained; verify the chain live.
      </p>
      <div className="mt-4">
        <ProvenancePanel trackingCode={trackingCode} />
      </div>
    </section>
  );
}

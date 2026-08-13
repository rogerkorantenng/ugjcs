import Link from "next/link";

/**
 * Rendered when a paper URL names a tracking code the archive does not hold — a mistyped
 * link, or a manuscript that was never published. Before this page existed, that URL
 * returned 200 and sat on the loading skeleton forever.
 */
export default function PaperNotFound() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-20 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-ink/50">Not in the archive</p>
      <h1 className="font-display-heading mt-3 text-2xl font-semibold text-ink">
        No published paper has that tracking code
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm text-ink/70">
        The link may be mistyped, or the manuscript it points to has not been published.
        Every published paper is listed in the archive.
      </p>
      <Link
        href="/search"
        className="mt-6 inline-block text-sm font-medium text-stamp underline decoration-stamp/40 underline-offset-4 hover:decoration-stamp"
      >
        Search the archive
      </Link>
    </main>
  );
}

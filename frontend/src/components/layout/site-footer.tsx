/** The colophon: the one place a scholarly journal states who publishes it. Without this,
 * the archive is a bare list of cards; with it, the list sits inside a masthead-to-footer
 * frame the way a print journal issue does. */
export function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-white/40">
      <div className="mx-auto max-w-3xl px-4 py-10 text-sm text-ink/60">
        <p className="font-serif text-sm font-semibold text-ink">University of Ghana Journal of Computing Science</p>
        <p className="mt-1.5 max-w-prose leading-relaxed">
          A double-blind peer-reviewed journal publishing original research in computing and
          information systems, from the Department of Computer Science, University of Ghana.
        </p>
        <p className="mt-6 font-mono text-xs uppercase tracking-[0.2em] text-ink/40">UGJCS</p>
      </div>
    </footer>
  );
}

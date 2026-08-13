/**
 * Mounted directly under every masthead in the app — the public `SiteHeader`, each
 * authenticated `AppNav`, and the login screen — so it is impossible to browse anywhere
 * without seeing it first. Styled in the same mono/uppercase register as the registry
 * stamp and tracking chips (small caps, tight tracking) and in plain ink on paper — the
 * `seal` red stays reserved for destructive decisions, and a red band directly under the
 * masthead's violet hairline clashed with it. The point is to look like a
 * notice this system would actually print, not a banner ad bolted on top of it. Not
 * dismissible on purpose — an exam-grading reader reloading a deep link must see it too, not
 * just a visitor who started at "/".
 */
export function DemoBanner() {
  return (
    <div role="note" className="border-b border-rule bg-surface text-ink">
      <p className="mx-auto flex max-w-5xl items-center justify-center gap-2.5 px-4 py-2 text-center text-xs leading-snug sm:text-sm">
        <span aria-hidden="true" className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-ink/50">
          Notice
        </span>
        <span aria-hidden="true" className="h-3 w-px bg-ink/20" />
        <span>
          <strong className="font-semibold text-seal">Capstone prototype, not an official system.</strong>{" "}
          <span className="text-ink/70">
            This is a student-built editorial portal for the Science and Development Journal
            (CBAS, University of Ghana) — not the journal&rsquo;s or the University&rsquo;s official
            system. Nothing submitted here is really peer-reviewed or published.
          </span>
        </span>
      </p>
    </div>
  );
}

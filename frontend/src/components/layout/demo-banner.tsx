/**
 * Mounted directly under every masthead in the app — the public `SiteHeader`, each
 * authenticated `AppNav`, and the login screen — so it is impossible to browse anywhere
 * without seeing it first. Styled in the same mono/uppercase register as the registry
 * stamp and tracking chips (small caps, tight tracking) and in `seal`, the palette's
 * existing destructive/attention tone, rather than a new red — the point is to look like a
 * notice this system would actually print, not a banner ad bolted on top of it. Not
 * dismissible on purpose — an exam-grading reader reloading a deep link must see it too, not
 * just a visitor who started at "/".
 */
export function DemoBanner() {
  return (
    <div role="note" className="border-b border-seal/30 bg-seal text-paper">
      <p className="mx-auto flex max-w-5xl items-center justify-center gap-2.5 px-4 py-2 text-center text-xs leading-snug sm:text-sm">
        <span aria-hidden="true" className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-paper/80">
          Notice
        </span>
        <span aria-hidden="true" className="h-3 w-px bg-paper/30" />
        <span>
          <strong className="font-semibold">Demo project, not a real journal.</strong>{" "}
          <span className="text-paper/90">
            UGJCS is a fictional publication built to demonstrate a software application for an
            Advanced Software Engineering exam — nothing submitted here is peer-reviewed or
            published for real.
          </span>
        </span>
      </p>
    </div>
  );
}

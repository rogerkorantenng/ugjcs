/**
 * Mounted directly under every masthead in the app — the public `SiteHeader`, each
 * authenticated `AppNav`, and the login screen — so it is impossible to browse anywhere
 * without seeing it first. Styled as a registry note, not a red apology banner bolted on
 * top: `ink` text on `paper`, the same hairline `rule` the rest of the chrome uses, with a
 * single `stamp`-coloured mark standing in for the physical "specimen / not for
 * circulation" stamp a real registry would ink across a demo file. Not dismissible on
 * purpose — a reader reloading a deep link must see it too, not just a visitor who started
 * at "/".
 */
export function DemoBanner() {
  return (
    <div role="note" className="border-b border-rule bg-paper">
      <p className="mx-auto flex max-w-5xl items-center justify-center gap-2.5 px-4 py-2 text-center text-xs leading-snug text-ink/70 sm:text-sm">
        <span
          aria-hidden="true"
          className="inline-flex shrink-0 items-center rounded-[2px] border border-stamp/40 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-stamp"
        >
          Specimen
        </span>
        <span>
          <strong className="font-semibold text-ink">Demo project, not a real journal.</strong>{" "}
          UGJCS is fictional, built to demonstrate a software application for an Advanced
          Software Engineering exam — nothing submitted here is peer-reviewed or published for real.
        </span>
      </p>
    </div>
  );
}

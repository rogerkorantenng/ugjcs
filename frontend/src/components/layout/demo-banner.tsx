/**
 * Mounted directly under every masthead in the app — the public `SiteHeader`, each
 * authenticated `AppNav`, and the login screen — so it is impossible to browse anywhere
 * without seeing it first. Uses `brick`, the palette's existing danger/error tone, rather
 * than a new red: the point is to look like it belongs to this system, not like a banner
 * ad bolted on top of it. Not dismissible on purpose — a exam-grading reader reloading a
 * deep link must see it too, not just a visitor who started at "/".
 */
export function DemoBanner() {
  return (
    <div role="note" className="border-b border-black/10 bg-brick text-paper">
      <p className="mx-auto flex max-w-5xl items-center justify-center gap-2 px-4 py-2 text-center text-xs font-medium leading-snug sm:text-sm">
        <span aria-hidden="true" className="text-sm">⚠</span>
        <span>
          <strong className="font-semibold">Demo project, not a real journal.</strong>{" "}
          UGJCS is a fictional publication built to demonstrate a software application for an
          Advanced Software Engineering exam — nothing submitted here is peer-reviewed or
          published for real.
        </span>
      </p>
    </div>
  );
}

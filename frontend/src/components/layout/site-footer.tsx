import Link from "next/link";

const FOOTER_LINKS = [
  { href: "/about", label: "About the portal" },
  { href: "/for-authors", label: "For authors" },
  { href: "/for-reviewers", label: "For reviewers" },
  { href: "/search", label: "Search the archive" },
  { href: "/login", label: "Sign in" },
];

/** The colophon: the one place a scholarly journal states who publishes it. Without this,
 * the archive is a bare list of cards; with it, the list sits inside a masthead-to-footer
 * frame the way a print journal issue does. Mirrors the masthead's rule-and-mono language
 * rather than inventing a new footer style, so the two ends of the page read as one cover. */
export function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-surface/60">
      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="grid gap-10 sm:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <p className="font-display-heading text-base font-semibold text-ink">
              Science and Development Journal
            </p>
            <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink/60">
              The editorial portal of the Science and Development Journal, published by the College
              of Basic and Applied Sciences, University of Ghana — submission, double-blind peer
              review, decisions and publishing in one place.
            </p>
          </div>
          <div className="text-sm">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink/40">The portal</p>
            <ul className="mt-2 space-y-1.5">
              {FOOTER_LINKS.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-ink/60 underline decoration-transparent underline-offset-4 transition-colors hover:text-stamp hover:decoration-stamp/40">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className="text-sm text-ink/60">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink/40">Editorial process</p>
            <p className="mt-2 leading-relaxed">
              Every submission is screened, sent to two independent reviewers under double-blind
              conditions, and decided on by an editor before a manuscript is scheduled and
              published.
            </p>
          </div>
        </div>
        <div className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-6">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-ink/40">SDJ</p>
          <p className="text-xs text-ink/45">
            Capstone prototype for an Advanced Software Engineering exam — not an official CBAS or
            University of Ghana system.
          </p>
        </div>
      </div>
    </footer>
  );
}

"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * The masthead: a print journal's nameplate rebuilt for the web — a small utility line
 * (the publisher's line every scholarly cover carries), the title set in the display
 * serif, and a double rule (a bold `stamp` hairline over a thin `rule` one) closing it
 * off, the way a real journal cover separates its nameplate from its table of contents.
 * Sits on the same `paper` ground as the rest of the page — a dark inverted bar was tried
 * and dropped: it read heavier than the rest of the cover, and `stamp` text set against
 * `ink` falls well short of AA contrast. That double rule is this app's one recurring
 * signature device; `AppNav` closes with the same pair so the authenticated dashboards
 * still read as the same publication.
 */
export function SiteHeader() {
  const pathname = usePathname();

  function navLink(href: string, label: string) {
    const active = pathname === href;
    return (
      <Link
        href={href}
        aria-current={active ? "page" : undefined}
        className={`group relative py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp ${
          active ? "text-stamp" : "text-ink/70 hover:text-ink"
        }`}
      >
        {label}
        <span
          aria-hidden="true"
          className={`absolute -bottom-0.5 left-0 h-px w-full origin-left bg-stamp transition-transform duration-300 ease-out ${
            active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"
          }`}
        />
      </Link>
    );
  }

  return (
    <header className="bg-paper text-ink">
      <div className="border-b border-rule">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/45">
          <span>Department of Computer Science · University of Ghana</span>
          <span className="hidden sm:inline">Est. 2026</span>
        </div>
      </div>
      <div className="mx-auto flex max-w-5xl flex-wrap items-end justify-between gap-x-6 gap-y-4 px-4 py-6">
        <Link href="/" className="rounded-[3px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp">
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-stamp">A double-blind peer-reviewed journal</p>
          <p className="font-display-wonk mt-1 max-w-lg font-serif text-2xl font-semibold leading-tight tracking-tight text-ink sm:text-[1.75rem]">
            University of Ghana Journal of Computing Science
          </p>
        </Link>
        <nav aria-label="Site" className="flex items-center gap-6 pb-1 text-sm font-medium">
          {navLink("/search", "Search")}
          {navLink("/login", "Sign in")}
        </nav>
      </div>
      <div aria-hidden="true" className="h-[3px] bg-stamp" />
      <div aria-hidden="true" className="h-px bg-rule" />
    </header>
  );
}

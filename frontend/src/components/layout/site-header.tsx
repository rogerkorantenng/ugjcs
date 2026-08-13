"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { roleHome } from "@/lib/role-home";
import type { SessionUser } from "@/types/api";

/**
 * The masthead: a registry cover rebuilt for the web — a small utility line (the
 * publisher's line every scholarly cover carries), the title set in the display face, and a
 * double rule (a gold hairline over a thin `rule` one) closing it off, the way a
 * real journal cover separates its nameplate from its table of contents. That double rule is
 * this app's one recurring structural motif; `AppNav` closes with the same pair so the
 * authenticated dashboards still read as the same publication.
 */
export function SiteHeader() {
  const pathname = usePathname();
  // The public pages stay statically rendered (the session cookie is httpOnly and never
  // read at build time), so the header asks the BFF who is signed in after mount. Until
  // the answer arrives it shows "Sign in" — the pre-session state — rather than nothing.
  const [user, setUser] = useState<SessionUser | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/me")
      .then((response) => (response.ok ? response.json() : { user: null }))
      .then((data: { user: SessionUser | null }) => {
        if (!cancelled) setUser(data.user);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  function navLink(href: string, label: string) {
    const active = pathname === href;
    return (
      <Link
        href={href}
        aria-current={active ? "page" : undefined}
        className={`group relative py-1 focus-visible:outline-2 focus-visible:outline-offset-2 ${
          active ? "text-ug-gold" : "text-paper/80 hover:text-paper"
        }`}
      >
        {label}
        <span
          aria-hidden="true"
          className={`absolute -bottom-0.5 left-0 h-px w-full origin-left bg-ug-gold transition-transform duration-300 ease-out ${
            active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"
          }`}
        />
      </Link>
    );
  }

  return (
    <header className="bg-ug-blue text-paper">
      <div className="border-b border-paper/10">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-paper/50">
          <span>College of Basic and Applied Sciences · University of Ghana</span>
          <span className="hidden sm:inline">Est. 2026</span>
        </div>
      </div>
      <div className="mx-auto flex max-w-5xl flex-wrap items-end justify-between gap-x-6 gap-y-4 px-4 py-6">
        <Link href="/" className="rounded-[3px] focus-visible:outline-2 focus-visible:outline-offset-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-ug-gold">Editorial portal · Double-blind peer review</p>
          <p className="font-display-heading mt-1 max-w-lg text-2xl font-semibold leading-tight tracking-tight sm:text-[1.75rem]">
            Science and Development Journal
          </p>
        </Link>
        <nav aria-label="Site" className="flex flex-wrap items-center gap-x-6 gap-y-2 pb-1 text-sm font-medium">
          {navLink("/about", "About")}
          {navLink("/for-authors", "For authors")}
          {navLink("/for-reviewers", "For reviewers")}
          {navLink("/search", "Search")}
          {user ? navLink(roleHome(user.roles), "My dashboard") : navLink("/login", "Sign in")}
        </nav>
      </div>
      <div aria-hidden="true" className="h-[3px] bg-ug-gold" />
      <div aria-hidden="true" className="h-px bg-paper/20" />
    </header>
  );
}

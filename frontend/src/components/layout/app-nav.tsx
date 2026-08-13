"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";
import { TOUR_START_EVENT } from "@/components/tour/tour";
import type { SessionUser } from "@/types/api";

// `tour` marks a link as an onboarding-tour anchor (`data-tour`): the author tour points
// at "Submit" from the dashboard, where the page itself has no submit button to spotlight.
const LINKS: Record<string, { href: string; label: string; tour?: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit", tour: "author-submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }, { href: "/editor/analytics", label: "Analytics" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }, { href: "/editor/analytics", label: "Analytics" }],
};

// Exactly the routes that mount a `<Tour>`; the "Show me around" trigger only renders
// where dispatching the start event will actually reach a listener.
const TOUR_ROOTS = new Set(["/author", "/reviewer", "/editor"]);

const ROLE_LABELS: Record<string, string> = {
  author: "Author",
  reviewer: "Reviewer",
  editor: "Editor",
  editor_in_chief: "Editor-in-Chief",
  administrator: "Administrator",
};

/** The dashboard's masthead. Same UG-blue chrome and closing double rule as `SiteHeader`, so
 * a reader moving from the public archive into a signed-in workspace never loses the sense
 * they are still inside the same portal — just past its front cover. */
export function AppNav({ user }: { user: SessionUser }) {
  const router = useRouter();
  const pathname = usePathname();
  const [signingOut, setSigningOut] = useState(false);
  const links = user.roles.flatMap((role) => LINKS[role] ?? []);
  // The longest matching href wins, so `/author/submit` highlights "Submit" rather than
  // also lighting up "My submissions" for the shared `/author` prefix.
  const activeHref = [...links]
    .sort((a, b) => b.href.length - a.href.length)
    .find((link) => pathname === link.href || pathname.startsWith(`${link.href}/`))?.href;
  const primaryRole = user.roles.includes("editor_in_chief") ? "editor_in_chief" : user.roles[0];

  async function signOut() {
    setSigningOut(true);
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="bg-ug-blue text-paper">
      <nav aria-label="Account navigation" className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-7">
          <Link
            href="/"
            className="font-display-heading text-sm font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            SDJ
          </Link>
          {links.map((link) => {
            const active = link.href === activeHref;
            return (
              <Link
                key={link.href}
                href={link.href}
                data-tour={link.tour}
                aria-current={active ? "page" : undefined}
                className={`group relative py-1 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  active ? "text-ug-gold" : "text-paper/75 hover:text-paper"
                }`}
              >
                {link.label}
                <span
                  aria-hidden="true"
                  className={`absolute -bottom-0.5 left-0 h-px w-full origin-left bg-ug-gold transition-transform duration-300 ease-out ${
                    active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"
                  }`}
                />
              </Link>
            );
          })}
        </div>
        <div className="flex items-center gap-4 text-sm text-paper/75">
          {TOUR_ROOTS.has(pathname) && (
            <button
              onClick={() => window.dispatchEvent(new Event(TOUR_START_EVENT))}
              className="font-medium text-paper/60 transition-colors hover:text-paper focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              Show me around
            </button>
          )}
          <span className="hidden items-center gap-2 sm:flex">
            {primaryRole && (
              <span className="rounded-full border border-ug-gold/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ug-gold">
                {ROLE_LABELS[primaryRole] ?? primaryRole}
              </span>
            )}
            <span className="font-mono text-xs">{user.email}</span>
          </span>
          <button
            onClick={signOut}
            disabled={signingOut}
            aria-busy={signingOut}
            className="inline-flex items-center gap-1.5 font-medium text-paper/85 transition-colors hover:text-paper focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {signingOut && <Spinner className="h-3.5 w-3.5" />}
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </nav>
      <div aria-hidden="true" className="h-[3px] bg-ug-gold" />
      <div aria-hidden="true" className="h-px bg-paper/20" />
    </header>
  );
}

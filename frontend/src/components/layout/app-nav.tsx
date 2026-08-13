"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AppNavSession } from "@/components/layout/app-nav-session";
import type { SessionUser } from "@/types/api";

// `tour` marks a link as an onboarding-tour anchor (`data-tour`): the author tour points
// at "Submit" from the dashboard, where the page itself has no submit button to spotlight.
const LINKS: Record<string, { href: string; label: string; tour?: string }[]> = {
  author: [{ href: "/author", label: "My submissions" }, { href: "/author/submit", label: "Submit", tour: "author-submit" }],
  reviewer: [{ href: "/reviewer", label: "My assignments" }],
  editor: [{ href: "/editor", label: "Screening queue" }, { href: "/editor/analytics", label: "Analytics" }],
  editor_in_chief: [{ href: "/editor", label: "Screening queue" }, { href: "/editor/analytics", label: "Analytics" }],
  administrator: [{ href: "/admin", label: "Accounts" }],
};

/** The dashboard's masthead. Same UG-blue chrome and closing double rule as `SiteHeader`, so
 * a reader moving from the public archive into a signed-in workspace never loses the sense
 * they are still inside the same portal — just past its front cover. */
export function AppNav({ user }: { user: SessionUser }) {
  const pathname = usePathname();
  const links = user.roles.flatMap((role) => LINKS[role] ?? []);
  // The longest matching href wins, so `/author/submit` highlights "Submit" rather than
  // also lighting up "My submissions" for the shared `/author` prefix.
  const activeHref = [...links]
    .sort((a, b) => b.href.length - a.href.length)
    .find((link) => pathname === link.href || pathname.startsWith(`${link.href}/`))?.href;

  return (
    <header className="bg-ug-blue text-paper">
      <nav aria-label="Account navigation" className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-7">
          <Link
            href="/search"
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
        <AppNavSession user={user} />
      </nav>
      <div aria-hidden="true" className="h-[3px] bg-ug-gold" />
      <div aria-hidden="true" className="h-px bg-paper/20" />
    </header>
  );
}

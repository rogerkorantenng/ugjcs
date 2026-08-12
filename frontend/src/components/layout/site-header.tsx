"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * The masthead: dark `ink` chrome under an `amber` hairline, the one place in the public
 * tier that departs from the `paper` background. A journal's cover carries its authority
 * before the reader gets to the contents page — this is that cover, rendered every page.
 */
export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="border-b border-amber/40 bg-ink text-paper">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-5">
        <Link
          href="/"
          className="font-serif text-lg font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
        >
          University of Ghana Journal of Computing Science
        </Link>
        <nav aria-label="Site" className="flex items-center gap-6 text-sm">
          <Link
            href="/search"
            aria-current={pathname === "/search" ? "page" : undefined}
            className={`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber ${
              pathname === "/search" ? "text-amber" : "text-paper/80 hover:text-paper"
            }`}
          >
            Search
          </Link>
          <Link
            href="/login"
            aria-current={pathname === "/login" ? "page" : undefined}
            className={`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber ${
              pathname === "/login" ? "text-amber" : "text-paper/80 hover:text-paper"
            }`}
          >
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  );
}

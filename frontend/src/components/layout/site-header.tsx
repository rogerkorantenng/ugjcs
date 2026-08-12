import Link from "next/link";

/**
 * The masthead: dark `ink` chrome under an `amber` hairline, the one place in the public
 * tier that departs from the `paper` background. A journal's cover carries its authority
 * before the reader gets to the contents page — this is that cover, rendered every page.
 */
export function SiteHeader() {
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
          <Link href="/search" className="text-paper/80 hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber">
            Search
          </Link>
          <Link href="/login" className="text-paper/80 hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber">
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  );
}

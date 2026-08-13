import Link from "next/link";

/**
 * The way back up: every detail page opens with one of these so a reader is never
 * stranded on a leaf route with only the browser chrome to escape through. Rendered
 * above the page's heading, in the same quiet register as other utility text.
 */
export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink/60 transition-colors hover:text-stamp focus-visible:outline-2 focus-visible:outline-offset-2"
    >
      <span aria-hidden="true">←</span> {label}
    </Link>
  );
}

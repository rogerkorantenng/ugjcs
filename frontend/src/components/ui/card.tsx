import type { HTMLAttributes } from "react";

const BASE = "rounded-[3px] border border-rule bg-white/70 shadow-[0_1px_2px_rgba(18,32,58,0.06)]";

/** The static container: a summary panel, a stat tile — anything that holds content but is
 * not itself a link. */
export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`${BASE} p-5 ${className}`} {...props} />;
}

/**
 * Classes for an interactive card that IS a link — every manuscript list item on the
 * author/reviewer dashboards and the public archive's `PaperCard`. Centralised so the
 * hover-lift reads identically everywhere a manuscript summary is clickable, the same way
 * `buttonClasses` centralises the button look.
 */
export function cardLinkClasses(className = "", padding: "p-4" | "p-5" = "p-4") {
  return `block ${BASE} ${padding} transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-teal/50
    hover:shadow-[0_10px_24px_rgba(18,32,58,0.1)] focus-visible:outline-none focus-visible:ring-2
    focus-visible:ring-amber ${className}`;
}

import type { HTMLAttributes } from "react";

const BASE = "rounded-[3px] border border-rule bg-surface shadow-[0_1px_2px_rgba(18,21,26,0.05)]";

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
  return `block ${BASE} ${padding} transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-stamp/50
    hover:shadow-[0_10px_24px_rgba(18,21,26,0.1)] focus-visible:outline-2
    focus-visible:outline-offset-2 ${className}`;
}

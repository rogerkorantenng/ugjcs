import type { ReactNode } from "react";

/** The one shape every empty list renders through: a dashed rule (never a bare border, so it
 * never gets mistaken for an unloaded card) and a serif title stating plainly what is
 * missing. A list rendering nothing at all reads as broken; this reads as "checked, and
 * empty". */
export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="mt-4 rounded-[3px] border border-dashed border-rule bg-white/40 px-6 py-10 text-center">
      <p className="font-serif text-base font-semibold text-ink">{title}</p>
      {hint && <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink/60">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

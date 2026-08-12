import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";

/** The accessible half of every skeleton below: sighted users read the shimmering shape,
 * screen reader users get a single polite announcement instead of a wall of unlabelled
 * `<div>`s. */
function StatusRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

/** Mirrors the author/reviewer assignment lists: a title bar, a tracking-code bar, and
 * (for the author dashboard, which shows a status) an optional badge-shaped bar. */
export function ManuscriptListSkeleton({
  count = 4,
  withBadge = true,
  label = "Loading…",
}: {
  count?: number;
  withBadge?: boolean;
  label?: string;
}) {
  return (
    <StatusRegion label={label}>
      <ul className="mt-4 space-y-3">
        {Array.from({ length: count }).map((_, i) => (
          <li key={i} className="flex items-center justify-between rounded-[3px] border border-rule bg-white/70 p-4">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-2/3 max-w-sm" />
              <Skeleton className="h-3 w-28" />
            </div>
            {withBadge && <Skeleton className="ml-4 h-5 w-24 shrink-0 rounded-full" />}
          </li>
        ))}
      </ul>
    </StatusRegion>
  );
}

/** Mirrors the editorial screening queue table: same column widths, same row rhythm. */
export function QueueTableSkeleton({ rows = 5, label = "Loading the queue…" }: { rows?: number; label?: string }) {
  return (
    <StatusRegion label={label}>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">Loading manuscripts</caption>
        <thead>
          <tr className="border-b border-rule text-ink/60">
            <th scope="col" className="py-2 font-medium">Tracking code</th>
            <th scope="col" className="font-medium">Title</th>
            <th scope="col" className="font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-b border-rule">
              <td className="py-2.5 pr-4"><Skeleton className="h-4 w-28" /></td>
              <td className="py-2.5 pr-4"><Skeleton className="h-4 w-64 max-w-full" /></td>
              <td className="py-2.5"><Skeleton className="h-5 w-24 rounded-full" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </StatusRegion>
  );
}

/** Mirrors a manuscript detail page: heading + badge, tracking chip, three lines of
 * abstract, one line of review-count metadata. Shared by the author, editor and reviewer
 * detail routes — they all render the same shape before their role-specific actions. */
export function ManuscriptDetailSkeleton({ label = "Loading manuscript…" }: { label?: string }) {
  return (
    <StatusRegion label={label}>
      <div className="flex items-start justify-between gap-4">
        <Skeleton className="h-7 w-2/3 max-w-md" />
        <Skeleton className="h-5 w-24 shrink-0 rounded-full" />
      </div>
      <Skeleton className="mt-2 h-4 w-32" />
      <div className="mt-5 space-y-2">
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-3/4" />
      </div>
      <Skeleton className="mt-4 h-3 w-40" />
    </StatusRegion>
  );
}

/** Mirrors a `PaperCard` grid on the public archive: tracking chip, two-line title, byline,
 * abstract snippet. */
export function ArchiveListSkeleton({ count = 5, label = "Loading papers…" }: { count?: number; label?: string }) {
  return (
    <StatusRegion label={label}>
      <div className="mt-6 grid gap-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="rounded-[3px] border border-rule bg-white/70 p-5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-3 h-5 w-3/4" />
            <Skeleton className="mt-2 h-3.5 w-1/3" />
            <Skeleton className="mt-3 h-3.5 w-full" />
            <Skeleton className="mt-1.5 h-3.5 w-2/3" />
          </div>
        ))}
      </div>
    </StatusRegion>
  );
}

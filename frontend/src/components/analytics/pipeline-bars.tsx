import { MANUSCRIPT_STATUSES, type ManuscriptStatus } from "@/types/api";
import type { EditorialAnalytics } from "@/types/analytics";

function statusLabel(status: ManuscriptStatus): string {
  const words = status.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * One horizontal bar per status with at least one manuscript, widths proportional to
 * the busiest status — plain divs, no chart library, matching the palette contract
 * (`stamp` for anything moving through the process). Statuses currently at zero are
 * collapsed into a single muted line rather than a stack of empty bars, so the chart's
 * height reflects the office's actual work in progress.
 */
export function PipelineBars({ analytics }: { analytics: EditorialAnalytics }) {
  const counts = MANUSCRIPT_STATUSES.map((status) => ({
    status,
    count: analytics.pipeline[status] ?? 0,
  }));
  const active = counts.filter((entry) => entry.count > 0);
  const empty = counts.filter((entry) => entry.count === 0);
  const max = Math.max(...active.map((entry) => entry.count), 1);

  return (
    <section className="mt-10">
      <h2 className="font-display-heading text-lg font-semibold text-ink">Pipeline</h2>
      <p className="mt-0.5 text-sm text-ink/60">Where every manuscript in the system stands right now.</p>

      {active.length === 0 ? (
        <p className="mt-4 text-sm text-ink/60">No manuscripts in the system yet.</p>
      ) : (
        <ul className="mt-4 space-y-2.5">
          {active.map(({ status, count }) => (
            <li key={status} className="grid grid-cols-[10rem_1fr_2.5rem] items-center gap-3 text-sm">
              <span className="truncate text-ink/80">{statusLabel(status)}</span>
              <span aria-hidden="true" className="h-2.5 overflow-hidden rounded-[3px] bg-ink/[0.05]">
                <span
                  className="block h-full rounded-[3px] bg-stamp/70"
                  style={{ width: `${Math.max((count / max) * 100, 2)}%` }}
                />
              </span>
              <span className="text-right font-mono text-xs text-ink/70">{count}</span>
            </li>
          ))}
        </ul>
      )}

      {empty.length > 0 && (
        <p className="mt-3 border-t border-rule pt-2.5 text-xs text-ink/40">
          None currently: {empty.map(({ status }) => statusLabel(status).toLowerCase()).join(", ")}
        </p>
      )}
    </section>
  );
}

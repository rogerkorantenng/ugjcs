import { formatMonth } from "@/lib/analytics-format";
import type { MonthCount } from "@/types/analytics";

/**
 * A mini column chart of submissions per month — plain divs on a flex baseline, no
 * chart library. Every column carries its count as visible text, so the sr-only
 * per-column sentence and the sighted reading never diverge.
 */
export function MonthChart({ months }: { months: MonthCount[] }) {
  const max = Math.max(...months.map((entry) => entry.count), 1);

  return (
    <section className="mt-10">
      <h2 className="font-display-heading text-lg font-semibold text-ink">Submissions by month</h2>
      {months.length === 0 ? (
        <p className="mt-4 text-sm text-ink/60">No submissions recorded yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <ul className="flex min-w-fit items-end gap-3 border-b border-rule pb-0 pt-2">
            {months.map((entry) => (
              <li key={entry.month} className="flex w-14 shrink-0 flex-col items-center gap-1">
                <span className="sr-only">{`${formatMonth(entry.month)}: ${entry.count} submission${entry.count === 1 ? "" : "s"}`}</span>
                <span aria-hidden="true" className="font-mono text-[10px] text-ink/70">{entry.count}</span>
                <span
                  aria-hidden="true"
                  className="block w-7 rounded-t-[3px] bg-stamp/70"
                  style={{ height: `${Math.max((entry.count / max) * 96, 3)}px` }}
                />
              </li>
            ))}
          </ul>
          <ul aria-hidden="true" className="flex min-w-fit gap-3 pt-1.5">
            {months.map((entry) => (
              <li key={entry.month} className="w-14 shrink-0 text-center font-mono text-[10px] uppercase tracking-[0.08em] text-ink/50">
                {formatMonth(entry.month)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

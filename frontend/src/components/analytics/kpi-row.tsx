import { Card } from "@/components/ui/card";
import { formatDays, formatPercent } from "@/lib/analytics-format";
import type { EditorialAnalytics } from "@/types/analytics";

/**
 * The three headline numbers. Each renders an em-dash — never a fake zero — while the
 * office has nothing to average yet, with a one-line note saying why, so an empty demo
 * database reads as "not yet" rather than "broken".
 */
export function KpiRow({ analytics }: { analytics: EditorialAnalytics }) {
  const kpis = [
    {
      label: "Acceptance rate",
      value: formatPercent(analytics.acceptance_rate),
      note: analytics.acceptance_rate === null ? "No decisions recorded yet." : null,
    },
    {
      label: "Avg days to decision",
      value: formatDays(analytics.avg_days_submission_to_decision),
      note: analytics.avg_days_submission_to_decision === null ? "No decisions recorded yet." : null,
    },
    {
      label: "Avg review turnaround",
      value: formatDays(analytics.avg_days_review_turnaround),
      note: analytics.avg_days_review_turnaround === null ? "No completed reviews yet." : null,
    },
  ];

  return (
    <div className="mt-6 grid gap-4 sm:grid-cols-3">
      {kpis.map((kpi) => (
        <Card key={kpi.label}>
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink/50">{kpi.label}</p>
          <p className="mt-2 font-display-heading text-3xl font-semibold text-ink">{kpi.value}</p>
          {kpi.note && <p className="mt-1 text-xs text-ink/50">{kpi.note}</p>}
        </Card>
      ))}
    </div>
  );
}

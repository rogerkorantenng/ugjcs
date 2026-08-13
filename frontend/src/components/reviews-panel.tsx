"use client";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import type { ReviewOut } from "@/types/api";

const CRITERIA: { key: keyof ReviewOut; label: string }[] = [
  { key: "originality_score", label: "Originality" },
  { key: "rigour_score", label: "Rigour" },
  { key: "clarity_score", label: "Clarity" },
  { key: "significance_score", label: "Significance" },
];

/**
 * The editor's view of what reviewers submitted — FR-11's four criterion scores, the
 * recommendation, and both comment fields. `confidential_comments_to_editor` renders
 * here because this panel lives only on `/editor/[trackingCode]`, a route no author or
 * reviewer session can reach; see `GET /editorial/{trackingCode}/reviews`'s docstring.
 */
export function ReviewsPanel({ trackingCode }: { trackingCode: string }) {
  const { data, error, isLoading } = useApi<ReviewOut[]>(`/api/editorial/${trackingCode}/reviews`);

  if (isLoading) return <p className="mt-3 text-sm text-ink/60">Loading reviews…</p>;
  if (error) {
    return (
      <div className="mt-3">
        <ProblemAlert
          problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Could not load reviews", status: 500 }}
        />
      </div>
    );
  }
  const submitted = (data ?? []).filter((review) => review.status === "submitted");
  if (submitted.length === 0) {
    return <p className="mt-3 text-sm text-ink/60">No reviews have been submitted yet.</p>;
  }

  return (
    <ul className="mt-3 space-y-4">
      {submitted.map((review) => (
        <li key={review.reviewer_id} className="rounded-[3px] border border-rule bg-white/70 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="font-serif text-base font-semibold text-ink">
              Recommendation: {review.recommendation?.replaceAll("_", " ")}
            </span>
          </div>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-ink/70 sm:grid-cols-4">
            {CRITERIA.map(({ key, label }) => (
              <div key={key} className="flex items-baseline justify-between gap-2 sm:block">
                <dt className="text-ink/50">{label}</dt>
                <dd className="font-mono tabular-nums text-ink">{String(review[key] ?? "—")}/5</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-sm leading-relaxed text-ink/80">{review.comments_to_author}</p>
          <div className="mt-3 border-l-2 border-stamp/40 bg-ink/[0.025] py-2 pl-3 text-sm leading-relaxed text-ink/80">
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">Confidential to editors</p>
            <p className="mt-1">{review.confidential_comments_to_editor}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

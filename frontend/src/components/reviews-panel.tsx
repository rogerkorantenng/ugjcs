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
        <li key={review.reviewer_id} className="rounded-[3px] border border-rule bg-surface/70 p-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="font-medium text-ink">Recommendation: {review.recommendation?.replaceAll("_", " ")}</span>
            {CRITERIA.map(({ key, label }) => (
              <span key={key} className="text-ink/70">{label}: {String(review[key] ?? "—")}/5</span>
            ))}
          </div>
          <p className="mt-2 text-sm text-ink/80">{review.comments_to_author}</p>
          <p className="mt-2 rounded-[3px] border-l-2 border-stamp bg-stamp/[0.06] p-2 text-sm text-ink/80">
            <span className="font-medium text-ink">Confidential to editors: </span>
            {review.confidential_comments_to_editor}
          </p>
        </li>
      ))}
    </ul>
  );
}

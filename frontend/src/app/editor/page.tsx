"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { QueueTableSkeleton } from "@/components/skeletons";
import type { Manuscript, ManuscriptStatus } from "@/types/api";

/**
 * Every status `GET /editorial/queue` can return (`_QUEUE_STATUSES`,
 * `backend/src/ugjcs/api/routers/editorial.py`), grouped by what an editor can do next —
 * see `domain/transitions.py` for which moves are legal from each. A manuscript never
 * disappears from this page just because it has been screened: that was the gap this
 * page exists to close.
 */
const QUEUE_SECTIONS: { status: ManuscriptStatus; title: string; hint: string }[] = [
  { status: "submitted", title: "Awaiting screening", hint: "Begin screening a new submission." },
  {
    status: "under_screening",
    title: "In screening",
    hint: "Assign a reviewer, desk reject, or send to review.",
  },
  {
    status: "under_review",
    title: "Under review",
    hint: "Waiting on reviewers — no editorial action needed yet.",
  },
  {
    status: "reviews_complete",
    title: "Reviews complete",
    hint: "Reviews are in; a decision is needed.",
  },
  {
    status: "revision_requested",
    title: "Revision requested",
    hint: "Waiting on the author to resubmit.",
  },
  {
    status: "resubmitted",
    title: "Resubmitted",
    hint: "The author has resubmitted — screen it or send it back to review.",
  },
  {
    status: "accepted",
    title: "Accepted",
    hint: "Ready for the Editor-in-Chief to schedule into an issue.",
  },
];

export default function EditorialQueue() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/editorial/queue");

  return (
    <>
      <h1 className="font-display-heading text-2xl font-semibold text-ink">Editorial queue</h1>

      {isLoading && <QueueTableSkeleton label="Loading the queue…" />}

      {error && (
        <div className="mt-4">
          <ProblemAlert
            problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
          />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          title="No manuscripts need editorial attention"
          hint="New submissions and manuscripts moving through review will appear here."
        />
      )}

      {data && data.length > 0 && (
        <div className="mt-4 space-y-8">
          {QUEUE_SECTIONS.map((section) => {
            const manuscripts = data.filter((m) => m.status === section.status);
            if (manuscripts.length === 0) return null;
            return (
              <section key={section.status}>
                <h2 className="font-display-heading text-lg font-semibold text-ink">
                  {section.title} <span className="ml-1 font-sans text-sm font-normal text-ink/50">({manuscripts.length})</span>
                </h2>
                <p className="mt-0.5 text-sm text-ink/60">{section.hint}</p>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[40rem] table-fixed text-left text-sm">
                    <caption className="sr-only">Manuscripts {section.title.toLowerCase()}</caption>
                    <colgroup>
                      <col className="w-44" />
                      <col />
                      <col className="w-40" />
                    </colgroup>
                    <thead>
                      <tr className="border-b border-rule text-ink/60">
                        <th scope="col" className="py-2 pr-4 font-medium">Tracking code</th>
                        <th scope="col" className="pr-4 font-medium">Title</th>
                        <th scope="col" className="text-right font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {manuscripts.map((manuscript) => (
                        <tr key={manuscript.tracking_code} className="border-b border-rule transition-colors hover:bg-stamp/5">
                          <td className="py-2.5 pr-4">
                            <Link
                              href={`/editor/${manuscript.tracking_code}`}
                              className="rounded-[3px] focus-visible:outline-2 focus-visible:outline-offset-2"
                            >
                              <TrackingChip code={manuscript.tracking_code} />
                            </Link>
                          </td>
                          <td className="truncate pr-4 text-ink">
                            <Link
                              href={`/editor/${manuscript.tracking_code}`}
                              className="rounded-[3px] hover:text-stamp focus-visible:outline-2 focus-visible:outline-offset-2"
                            >
                              {manuscript.title}
                            </Link>
                          </td>
                          <td className="text-right"><StatusBadge status={manuscript.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}

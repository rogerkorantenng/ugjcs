"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import { EmptyState } from "@/components/ui/empty-state";
import { QueueTableSkeleton } from "@/components/skeletons";
import type { Manuscript } from "@/types/api";

export default function EditorialQueue() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/editorial/queue");

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">Screening queue</h1>

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
          title="No manuscripts awaiting screening"
          hint="New submissions will appear here as authors send them in."
        />
      )}

      {data && data.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-[3px] border border-rule bg-white/70 shadow-[0_1px_2px_rgba(18,32,58,0.06)]">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <caption className="sr-only">Manuscripts awaiting editorial action</caption>
              <thead>
                <tr className="border-b border-rule bg-ink/[0.03] text-ink/60">
                  <th scope="col" className="py-2.5 pl-4 pr-4 font-medium">Tracking code</th>
                  <th scope="col" className="pr-4 font-medium">Title</th>
                  <th scope="col" className="pr-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.map((manuscript) => (
                  <tr key={manuscript.tracking_code} className="border-b border-rule last:border-b-0 transition-colors hover:bg-teal/5">
                    <td className="py-2.5 pl-4 pr-4">
                      <Link
                        href={`/editor/${manuscript.tracking_code}`}
                        className="rounded-[3px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
                      >
                        <TrackingChip code={manuscript.tracking_code} />
                      </Link>
                    </td>
                    <td className="pr-4 text-ink">{manuscript.title}</td>
                    <td className="pr-4"><StatusBadge status={manuscript.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

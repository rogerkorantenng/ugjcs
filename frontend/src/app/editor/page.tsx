"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { StatusBadge } from "@/components/ui/badge";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import type { Manuscript } from "@/types/api";

export default function EditorialQueue() {
  const { data, error, isLoading } = useApi<Manuscript[]>("/api/editorial/queue");
  if (isLoading) return <p>Loading the queue…</p>;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">Screening queue</h1>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">Manuscripts awaiting editorial action</caption>
        <thead>
          <tr className="border-b border-rule text-ink/60">
            <th scope="col" className="py-2 font-medium">Tracking code</th>
            <th scope="col" className="font-medium">Title</th>
            <th scope="col" className="font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((manuscript) => (
            <tr key={manuscript.tracking_code} className="border-b border-rule">
              <td className="py-2">
                <Link
                  href={`/editor/${manuscript.tracking_code}`}
                  className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
                >
                  <TrackingChip code={manuscript.tracking_code} />
                </Link>
              </td>
              <td className="text-ink">{manuscript.title}</td>
              <td><StatusBadge status={manuscript.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {data && data.length === 0 && <p className="mt-4 text-ink/60">Nothing awaiting screening.</p>}
    </>
  );
}

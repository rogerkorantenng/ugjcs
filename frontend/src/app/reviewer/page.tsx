"use client";
import Link from "next/link";
import { useApi, ClientApiError } from "@/lib/use-api";
import { ProblemAlert } from "@/components/ui/alert";
import { TrackingChip } from "@/components/ui/tracking-chip";
import type { BlindedManuscript } from "@/types/api";

export default function ReviewerAssignments() {
  const { data, error, isLoading } = useApi<BlindedManuscript[]>("/api/reviews");
  if (isLoading) return <p>Loading your assignments…</p>;
  if (error)
    return (
      <ProblemAlert
        problem={error instanceof ClientApiError ? error.problem : { type: "about:blank", title: "Something went wrong", status: 500 }}
      />
    );

  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-ink">My review assignments</h1>
      {data && data.length === 0 && <p className="mt-4 text-ink/60">You have no assignments right now.</p>}
      <ul className="mt-4 space-y-3">
        {data?.map((manuscript) => (
          <li key={manuscript.tracking_code}>
            <Link
              href={`/reviewer/${manuscript.tracking_code}`}
              className="block rounded-[3px] border border-rule bg-white/70 p-4 hover:border-teal/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber"
            >
              <p className="font-medium text-ink">{manuscript.title}</p>
              <TrackingChip code={manuscript.tracking_code} className="mt-1" />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

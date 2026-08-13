import { NextResponse } from "next/server";
import { backendFetch, ProblemDetailsError } from "@/lib/backend";
import type { ProvenanceOut } from "@/types/scholarly";

/**
 * Public proxy for `GET /archive/{code}/provenance` (published papers only, upstream).
 * Deliberately `no-store` in both directions: the whole point of the "Verify chain"
 * button is that the backend re-verifies the hash chain *live* at click time — serving
 * a cached verdict would quietly turn the feature into theatre.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const provenance = await backendFetch<ProvenanceOut>(`/archive/${trackingCode}/provenance`, {
      cache: "no-store",
    });
    return NextResponse.json(provenance, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

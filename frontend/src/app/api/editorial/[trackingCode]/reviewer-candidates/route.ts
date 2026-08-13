import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewerCandidate } from "@/types/api";

/**
 * `GET /api/editorial/{trackingCode}/reviewer-candidates` — proxies the upstream route of
 * the same shape. Editor/EiC-only upstream; this route does not itself re-check the role,
 * the same way every other `/api/editorial/*` route in this app defers that to the backend.
 * Backs the reviewer-assignment picker: candidates with an `excluded_reason` are still
 * returned (never filtered out here) so the picker can show *why* someone is ineligible
 * instead of silently omitting them.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const candidates = await authedFetch<ReviewerCandidate[]>(`/editorial/${trackingCode}/reviewer-candidates`);
    return NextResponse.json(candidates);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

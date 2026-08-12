import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewOut } from "@/types/api";

/**
 * The editor-only view of what reviewers submitted, confidential comments included —
 * `GET /editorial/{trackingCode}/reviews` (`Action.DECIDE`-gated upstream, the same
 * grant `record_decision` requires). No author-facing route in this app ever calls
 * this one, which is what keeps `confidential_comments_to_editor` from an author.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    return NextResponse.json(await authedFetch<ReviewOut[]>(`/editorial/${trackingCode}/reviews`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

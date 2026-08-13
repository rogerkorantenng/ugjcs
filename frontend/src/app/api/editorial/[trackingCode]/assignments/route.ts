import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewAssignment } from "@/types/analytics";

/**
 * Who is reviewing one manuscript and where each review stands against its deadline —
 * `GET /editorial/{trackingCode}/assignments`, editor/EiC only upstream. Feeds the
 * detail page's "Assigned reviewers" panel and the queue's overdue chips.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    return NextResponse.json(await authedFetch<ReviewAssignment[]>(`/editorial/${trackingCode}/assignments`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

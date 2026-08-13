import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { ReviewerPerformance } from "@/types/analytics";

/**
 * Per-reviewer load and turnaround for the analytics page's performance table —
 * `GET /editorial/reviewer-performance`, editor/EiC only upstream.
 */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<ReviewerPerformance[]>("/editorial/reviewer-performance"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

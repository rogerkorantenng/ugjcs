import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

/**
 * No request body. Backend-enforced: `Action.PUBLISH`, granted to `editor_in_chief` alone,
 * and legal only from `scheduled` (`backend/src/ugjcs/domain/transitions.py`).
 */
export async function POST(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const result = await authedFetch<Manuscript>(`/editorial/${trackingCode}/publish`, { method: "POST" });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

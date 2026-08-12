import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

/**
 * Every manuscript still awaiting some editorial action — `submitted` through
 * `accepted` — not only fresh submissions. See `_QUEUE_STATUSES` in
 * `backend/src/ugjcs/api/routers/editorial.py`; there is no `?status=` filter upstream.
 */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<Manuscript[]>("/editorial/queue"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

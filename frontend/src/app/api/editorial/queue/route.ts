import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

/** Hardcoded to `status == submitted` upstream — Plan 4 has no `?status=` filter. */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<Manuscript[]>("/editorial/queue"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { EditorialAnalytics } from "@/types/analytics";

/**
 * Pipeline counts, monthly submission volumes, and the office's headline averages —
 * `GET /editorial/analytics`, editor/EiC only upstream. Read-only aggregate; nothing
 * here mutates, so the plain `authedFetch` proxy idiom is all it needs.
 */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<EditorialAnalytics>("/editorial/analytics"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

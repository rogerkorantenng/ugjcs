import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { BlindedManuscript } from "@/types/api";

/**
 * `GET /reviews/mine` returns the blinded manuscripts directly (docs/05-api-contract.md
 * §6) — there is no assignment-summary wrapper and no separate per-assignment id; the
 * manuscript's own `tracking_code` is the only handle a reviewer has on an assignment.
 */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<BlindedManuscript[]>("/reviews/mine"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

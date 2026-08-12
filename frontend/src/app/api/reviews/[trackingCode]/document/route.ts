import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { DocumentUrlOut } from "@/types/api";

/**
 * The reviewer's document link — and the *only* document route a reviewer's manuscript
 * page may ever call. `GET /reviews/{trackingCode}/document` has no `variant` parameter on
 * the backend at all: it always serves the anonymised copy, structurally, the same way
 * `BlindedManuscript` has no author field to leak. Never point a reviewer-facing component
 * at `/api/manuscripts/{trackingCode}/document` instead — that route can serve the
 * original, and doing so would defeat the double-blind guarantee this whole route exists
 * to enforce.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const document = await authedFetch<DocumentUrlOut>(`/reviews/${trackingCode}/document`);
    return NextResponse.redirect(document.url);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

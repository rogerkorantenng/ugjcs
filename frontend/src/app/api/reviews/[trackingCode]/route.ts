import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";

/**
 * `POST /reviews/{tracking_code}/submit` — not `/reviews/{assignmentId}` (docs/05-api-contract.md
 * §6). There is no GET here: Plan 4 has no per-assignment detail route, only the list at
 * `/reviews/mine` — the reviewer detail page reads the manuscript out of that list.
 */
export async function POST(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const body = await request.text();
    await authedFetch(`/reviews/${trackingCode}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

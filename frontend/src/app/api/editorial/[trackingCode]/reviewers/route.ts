import { NextResponse } from "next/server";
import { z } from "zod";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";

const AssignInput = z.object({ reviewer_id: z.string().min(1) });

/**
 * Path is `/reviewers`, not `/assign`; body is `{reviewer_id}` only — no `due_date` — and
 * the response is empty (204), not a manuscript (docs/05-api-contract.md §6). There is no
 * `GET /editorial/reviewer-candidates` endpoint anywhere in Plan 4: reviewer assignment is
 * a persistence-only record with no scoring, no exclusion check, no candidate list.
 */
export async function POST(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const parsed = AssignInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }
  try {
    await authedFetch(`/editorial/${trackingCode}/reviewers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

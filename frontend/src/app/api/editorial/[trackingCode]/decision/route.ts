import { NextResponse } from "next/server";
import { z } from "zod";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import { DECISION_TYPES, type Manuscript } from "@/types/api";

const DecisionInput = z.object({
  decision: z.enum(DECISION_TYPES),
  rationale: z.string().min(1),
});

/**
 * Path is `/decision`, not `/decide` (docs/05-api-contract.md §6). A desk rejection is
 * `decision: "desk_reject"` on this same endpoint — there is no separate screening-with-
 * rejection call.
 */
export async function POST(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const parsed = DecisionInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }
  try {
    const result = await authedFetch<Manuscript>(`/editorial/${trackingCode}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

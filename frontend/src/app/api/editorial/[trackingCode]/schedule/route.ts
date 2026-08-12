import { NextResponse } from "next/server";
import { z } from "zod";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

const ScheduleInput = z.object({
  volume: z.number().int().positive(),
  number: z.number().int().positive(),
});

/**
 * `{volume, number}` — the backend derives an `IssueId` from the pair deterministically
 * rather than looking one up (issues are not a persisted entity). Backend-enforced:
 * `Action.PUBLISH`, granted to `editor_in_chief` alone, and legal only from `accepted`
 * (`backend/src/ugjcs/domain/transitions.py`); this route relays whatever the backend
 * decides rather than re-checking either itself.
 */
export async function POST(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const parsed = ScheduleInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }
  try {
    const result = await authedFetch<Manuscript>(`/editorial/${trackingCode}/schedule`, {
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

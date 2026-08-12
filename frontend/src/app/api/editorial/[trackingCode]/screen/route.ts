import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

/** No request body — moves `submitted` to `under_screening` (docs/05-api-contract.md §6). */
export async function POST(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const result = await authedFetch<Manuscript>(`/editorial/${trackingCode}/screen`, { method: "POST" });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

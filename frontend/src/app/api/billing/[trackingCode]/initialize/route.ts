import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { BillingInitializeOut } from "@/types/wave2";

/** No request body. Returns either a Paystack `authorization_url` for the browser to
 * follow, or `{"mock": true}` — the mock gateway has already settled the charge. */
export async function POST(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const result = await authedFetch<BillingInitializeOut>(`/billing/${trackingCode}/initialize`, { method: "POST" });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

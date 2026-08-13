import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { BillingInvoice } from "@/types/wave2";

/** Editor-in-Chief only — the backend enforces the role; this proxy only forwards. */
export async function POST(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const result = await authedFetch<BillingInvoice | undefined>(`/billing/${trackingCode}/waive`, { method: "POST" });
    return result === undefined ? new NextResponse(null, { status: 204 }) : NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

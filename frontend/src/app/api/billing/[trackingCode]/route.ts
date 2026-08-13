import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { BillingInvoice } from "@/types/wave2";

/** A 404 here is a normal answer — "no invoice raised yet" — and is passed through as-is
 * for the APC panel to render as a quiet note, not an error. */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    return NextResponse.json(await authedFetch<BillingInvoice>(`/billing/${trackingCode}`));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

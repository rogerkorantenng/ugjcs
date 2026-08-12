import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { DocumentUrlOut } from "@/types/api";

/**
 * The author's/editor's original-document link. The live API answers with a JSON
 * `{url, expires_in_seconds}` body (200), not an HTTP redirect — this route fetches that
 * server-side (so the bearer token never reaches the browser) and turns it into a redirect
 * to the pre-signed S3 URL, which is what a plain `<a href>` on the manuscript page needs.
 * No `variant` query param is forwarded: this route only ever requests the default
 * `original` copy, never `anonymised` — that path is a reviewer's alone
 * (`/api/reviews/{trackingCode}/document`), and it is a separate backend route by shape,
 * not merely by query parameter.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const document = await authedFetch<DocumentUrlOut>(`/manuscripts/${trackingCode}/document`);
    return NextResponse.redirect(document.url);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

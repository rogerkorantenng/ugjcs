import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { DocumentUrlOut } from "@/types/api";

/**
 * The author's/editor's original-document link. The live API answers with a JSON
 * `{url, expires_in_seconds}` body (200), not an HTTP redirect. By default this route
 * fetches that server-side (so the bearer token never reaches the browser) and turns it
 * into a redirect to the pre-signed S3 URL, which is what a plain `<a href>` "download"
 * link needs.
 *
 * `?format=json` instead returns that `DocumentUrlOut` body directly, `Cache-Control:
 * no-store` — the inline `<PdfViewer>` needs the raw URL (not a redirect a browser has
 * already followed) so it can re-fetch a fresh one on demand once the ~5 minute pre-signed
 * URL expires. Never cache this response: lengthening its effective lifetime would widen
 * the pre-signed URL's exposure window, which is the whole security property it has.
 *
 * No `variant` query param is forwarded: this route only ever requests the default
 * `original` copy, never `anonymised` — that path is a reviewer's alone
 * (`/api/reviews/{trackingCode}/document`), and it is a separate backend route by shape,
 * not merely by query parameter.
 */
export async function GET(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const asJson = new URL(request.url).searchParams.get("format") === "json";
  try {
    const document = await authedFetch<DocumentUrlOut>(`/manuscripts/${trackingCode}/document`);
    if (asJson) {
      return NextResponse.json(document, { headers: { "Cache-Control": "no-store" } });
    }
    return NextResponse.redirect(document.url);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

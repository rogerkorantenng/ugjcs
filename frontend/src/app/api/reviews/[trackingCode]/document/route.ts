import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { DocumentUrlOut } from "@/types/api";

/**
 * The reviewer's document link — and the *only* document route a reviewer's manuscript
 * page may ever call. `GET /reviews/{trackingCode}/document` has no `variant` parameter on
 * the backend at all: it always serves the anonymised copy, structurally, the same way
 * `BlindedManuscript` has no author field to leak. Never point a reviewer-facing component
 * at `/api/manuscripts/{trackingCode}/document` instead — that route can serve the
 * original, and doing so would defeat the double-blind guarantee this whole route exists
 * to enforce.
 *
 * `?format=json` returns the `DocumentUrlOut` body directly (`Cache-Control: no-store`)
 * instead of redirecting, for the inline `<PdfViewer>` — see the sibling manuscripts route
 * for the full rationale. The reviewer's viewer chrome renders a `RedactedAuthorSlot`
 * alongside this document; the anonymised PDF itself carrying no `/Title`/`/Author` is what
 * keeps the browser's own PDF toolbar from re-leaking identity — see
 * `src/lib/pdf-metadata.test.ts`.
 */
export async function GET(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const asJson = new URL(request.url).searchParams.get("format") === "json";
  try {
    const document = await authedFetch<DocumentUrlOut>(`/reviews/${trackingCode}/document`);
    if (asJson) {
      return NextResponse.json(document, { headers: { "Cache-Control": "no-store" } });
    }
    return NextResponse.redirect(document.url);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

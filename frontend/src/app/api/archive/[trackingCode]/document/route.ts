import { NextResponse } from "next/server";
import { backendFetch, ProblemDetailsError } from "@/lib/backend";
import type { DocumentUrlOut } from "@/types/api";

/**
 * FR-18: a reader downloads a published paper's PDF, no sign-in required. Uses
 * `backendFetch`, not `authedFetch` — this route must work for an anonymous visitor,
 * the same way the rest of `/api/archive/*` never attaches a token. The live API answers
 * with a JSON `{url, expires_in_seconds}` body (200), not a redirect; this route fetches
 * that server-side and turns it into a redirect for a plain `<a href>` to follow, the
 * same pattern `/api/manuscripts/{trackingCode}/document` and
 * `/api/reviews/{trackingCode}/document` already use.
 *
 * `GET /archive/{trackingCode}/document` upstream only ever serves a `PUBLISHED`
 * manuscript's original PDF — see `ugjcs.api.routers.archive.download_published_document`
 * — so this route can never be pointed at a paper still anywhere in the workflow.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  try {
    const document = await backendFetch<DocumentUrlOut>(`/archive/${trackingCode}/document`);
    return NextResponse.redirect(document.url);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

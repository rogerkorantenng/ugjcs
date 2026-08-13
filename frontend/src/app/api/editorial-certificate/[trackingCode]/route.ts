import { NextResponse } from "next/server";
import { env } from "@/lib/env";
import { getSession } from "@/lib/session";
import type { ProblemDetails } from "@/types/api";

/**
 * Streams the decision certificate PDF (`GET /editorial-certificate/{trackingCode}`)
 * through to the browser with its content type preserved, so a plain `<a href>` on the
 * editor's detail page downloads it without the bearer token ever reaching the client.
 *
 * This can't use `authedFetch` — that helper parses JSON — so it holds the same
 * session-cookie contract inline and pipes `response.body` straight through. Unlike
 * `authedFetch` there is no token-refresh retry here: the page that renders the link
 * has already made refreshing JSON calls through `authedFetch`, so a live session's
 * token is fresh by the time anyone clicks; a genuinely dead session gets the same
 * 401 problem every other route returns.
 *
 * A 409 (no decision recorded yet) arrives as a JSON problem body upstream and is
 * passed through as one — the UI only renders the link once a decision exists, so
 * hitting it means a stale page, and the problem text says so.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const session = await getSession();
  if (!session.accessToken || !session.user) {
    return NextResponse.json(
      { type: "about:blank", title: "Not signed in", status: 401 } satisfies ProblemDetails,
      { status: 401 },
    );
  }

  const response = await fetch(`${env.API_BASE_URL}/editorial-certificate/${trackingCode}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
  });

  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as ProblemDetails | null;
    return NextResponse.json(
      problem ?? { type: "about:blank", title: response.statusText, status: response.status },
      { status: response.status },
    );
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/pdf",
      "Content-Disposition":
        response.headers.get("Content-Disposition") ??
        `attachment; filename="decision-certificate-${trackingCode}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}

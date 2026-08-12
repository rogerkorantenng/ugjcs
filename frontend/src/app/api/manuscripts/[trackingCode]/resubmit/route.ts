import { NextResponse } from "next/server";
import { authedFetchStream } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

/**
 * Multipart only — `file` (the revised PDF) and `response_to_reviewers`. Backend-enforced
 * ownership (`Action.RESUBMIT` — corresponding author only) and lifecycle (only legal from
 * `revision_requested`, per `backend/src/ugjcs/domain/transitions.py`); this route relays
 * whatever the backend decides rather than re-checking either itself. Streams the incoming
 * body straight through, same as `POST /api/manuscripts`.
 */
export async function POST(request: Request, { params }: { params: Promise<{ trackingCode: string }> }) {
  const { trackingCode } = await params;
  const contentType = request.headers.get("content-type");
  if (!contentType?.startsWith("multipart/form-data")) {
    return NextResponse.json(
      {
        type: "about:blank",
        title: "Invalid input",
        status: 422,
        detail: "Expected a multipart/form-data submission with a revised manuscript file attached.",
      },
      { status: 422 },
    );
  }
  try {
    const manuscript = await authedFetchStream<Manuscript>(`/manuscripts/${trackingCode}/resubmit`, {
      method: "POST",
      body: request.body,
      contentType,
    });
    return NextResponse.json(manuscript);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

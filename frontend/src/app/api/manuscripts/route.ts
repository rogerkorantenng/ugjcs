import { NextResponse } from "next/server";
import { authedFetch, authedFetchStream } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

export async function GET() {
  try {
    return NextResponse.json(await authedFetch<Manuscript[]>("/manuscripts/mine"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

/**
 * Multipart only — the live API requires `title`, `abstract`, `file` (a PDF) and accepts
 * `keywords`/`co_author_ids` as the rest of the form fields (this supersedes
 * docs/05-api-contract.md §6, which still describes a JSON-only body; see the frontend
 * wiring notes for the full discrepancy). The incoming request's body is forwarded to the
 * backend as a stream via `authedFetchStream` — this route never buffers the uploaded file
 * into memory itself, so it never re-parses the multipart body into a JS `FormData` either.
 */
export async function POST(request: Request) {
  const contentType = request.headers.get("content-type");
  if (!contentType?.startsWith("multipart/form-data")) {
    return NextResponse.json(
      {
        type: "about:blank",
        title: "Invalid input",
        status: 422,
        detail: "Expected a multipart/form-data submission with a manuscript file attached.",
      },
      { status: 422 },
    );
  }
  try {
    const manuscript = await authedFetchStream<Manuscript>("/manuscripts", {
      method: "POST",
      body: request.body,
      contentType,
    });
    return NextResponse.json(manuscript, { status: 201 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

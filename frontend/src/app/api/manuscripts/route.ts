import { NextResponse } from "next/server";
import { z } from "zod";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { Manuscript } from "@/types/api";

const SubmitInput = z.object({
  title: z.string().min(5),
  abstract: z.string().min(100),
  keywords: z.array(z.string()),
  co_author_ids: z.array(z.string().uuid()).default([]),
});

export async function GET() {
  try {
    return NextResponse.json(await authedFetch<Manuscript[]>("/manuscripts/mine"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

/** JSON only — Plan 4 has no file storage anywhere, so there is no attachment to forward. */
export async function POST(request: Request) {
  const parsed = SubmitInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }
  try {
    const manuscript = await authedFetch<Manuscript>("/manuscripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    return NextResponse.json(manuscript, { status: 201 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

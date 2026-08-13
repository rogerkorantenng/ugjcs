import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { PersonLookup } from "@/types/api";

/**
 * `GET /api/people/lookup?email=` — proxies `GET /people/lookup?email=` upstream. Any
 * authenticated user may call this; it backs the submission form's add-by-email co-author
 * picker. A miss is a normal, expected outcome (the address hasn't registered, or was
 * mistyped) — relayed as the same 404 the backend returns, not upgraded into a 500.
 */
export async function GET(request: Request) {
  const email = new URL(request.url).searchParams.get("email");
  if (!email) {
    return NextResponse.json(
      { type: "about:blank", title: "An email address is required", status: 422 },
      { status: 422 },
    );
  }
  try {
    const person = await authedFetch<PersonLookup>(`/people/lookup?email=${encodeURIComponent(email)}`);
    return NextResponse.json(person);
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

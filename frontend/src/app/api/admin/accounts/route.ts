import { NextResponse } from "next/server";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { AdminAccount } from "@/types/wave2";

/** Administrator only — the backend enforces the role; this proxy only forwards. */
export async function GET() {
  try {
    return NextResponse.json(await authedFetch<AdminAccount[]>("/admin/accounts"));
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

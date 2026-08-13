import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { authedFetch } from "@/lib/auth-fetch";
import { ProblemDetailsError } from "@/lib/backend";
import type { SessionUser } from "@/types/api";

/**
 * Who is signed in, according to a session the BACKEND still recognises. The sealed
 * cookie alone is not enough: after the demo database is wiped and reseeded, a stale
 * cookie still decrypts to a user whose account no longer exists — trusting it left the
 * header showing "My dashboard" and the sign-in page bouncing to a dashboard that could
 * load nothing. Validating here lets `authedFetch` destroy the dead session (it clears
 * the cookie when refresh fails), so one probe heals the browser.
 */
export async function GET() {
  const session = await getSession();
  if (!session.user) return NextResponse.json({ user: null });
  try {
    await authedFetch<{ id: string; roles: SessionUser["roles"] }>("/auth/me");
    return NextResponse.json({ user: session.user });
  } catch (error) {
    if (error instanceof ProblemDetailsError && error.status === 401) {
      return NextResponse.json({ user: null });
    }
    throw error;
  }
}

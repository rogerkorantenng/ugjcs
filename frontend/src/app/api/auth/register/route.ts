import { NextResponse } from "next/server";
import { z } from "zod";
import { getSession } from "@/lib/session";
import { backendFetch, ProblemDetailsError } from "@/lib/backend";
import { decodeAccessTokenExpiry } from "@/lib/auth-fetch";
import type { SessionUser } from "@/types/api";

const RegisterInput = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  full_name: z.string().min(1),
  affiliation: z.string().min(1),
});

interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface MeResponse {
  id: string;
  roles: SessionUser["roles"];
}

/**
 * Self-service sign-up. The backend registers, grants AUTHOR, and returns a signed-in
 * token pair; this route then establishes the same first-party session the login route
 * does, so a new author lands on their dashboard with no second step.
 */
export async function POST(request: Request) {
  const parsed = RegisterInput.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(
      { type: "about:blank", title: "Invalid input", status: 422, detail: parsed.error.issues[0]?.message },
      { status: 422 },
    );
  }

  try {
    const pair = await backendFetch<TokenPairResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(parsed.data),
    });
    const me = await backendFetch<MeResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${pair.access_token}` },
    });
    const user: SessionUser = { id: me.id, email: parsed.data.email, roles: me.roles };

    const session = await getSession();
    session.user = user;
    session.accessToken = pair.access_token;
    session.refreshToken = pair.refresh_token;
    session.accessTokenExpiresAt = decodeAccessTokenExpiry(pair.access_token);
    await session.save();
    return NextResponse.json({ user }, { status: 201 });
  } catch (error) {
    if (error instanceof ProblemDetailsError) return NextResponse.json(error.problem, { status: error.status });
    throw error;
  }
}

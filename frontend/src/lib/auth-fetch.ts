import "server-only";
import { env } from "@/lib/env";
import { getSession, type SessionData } from "@/lib/session";
import { ProblemDetailsError } from "@/lib/backend";
import type { IronSession } from "iron-session";
import type { ProblemDetails } from "@/types/api";

async function toProblem(response: Response): Promise<ProblemDetails> {
  try {
    return (await response.json()) as ProblemDetails;
  } catch {
    return { type: "about:blank", title: response.statusText, status: response.status };
  }
}

interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/**
 * Reads the `exp` claim (seconds since epoch) out of the access token's JWT payload,
 * without verifying the signature — this process never holds the signing secret, and the
 * backend re-verifies every call anyway. Plan 4's `TokenPairOut` carries no `expires_in`,
 * so the JWT's own `exp` claim (Plan 3, `JwtTokenService`) is the only source of truth for
 * when to schedule a proactive refresh.
 */
export function decodeAccessTokenExpiry(token: string): number {
  const payload = token.split(".")[1];
  const claims = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { exp: number };
  return claims.exp * 1000;
}

async function refresh(session: IronSession<SessionData>): Promise<void> {
  const response = await fetch(`${env.API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refreshToken }),
  });
  if (!response.ok) {
    session.destroy();
    throw new ProblemDetailsError(
      { type: "about:blank", title: "Your session has expired", status: 401 },
      401,
    );
  }
  const data = (await response.json()) as TokenPairResponse;
  session.accessToken = data.access_token;
  session.refreshToken = data.refresh_token;
  session.accessTokenExpiresAt = decodeAccessTokenExpiry(data.access_token);
  await session.save();
}

/**
 * Used only inside Route Handlers, where cookie writes are allowed. Proactively refreshes
 * a token about to expire, and retries once on a 401 the proactive check missed — clock
 * skew between this process and the backend is the reason a reactive path still exists.
 */
export async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = await getSession();
  if (!session.accessToken || !session.user) {
    throw new ProblemDetailsError(
      { type: "about:blank", title: "Not signed in", status: 401 },
      401,
    );
  }
  if (session.accessTokenExpiresAt && session.accessTokenExpiresAt < Date.now() + 5_000) {
    await refresh(session);
  }

  const attempt = () =>
    fetch(`${env.API_BASE_URL}${path}`, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${session.accessToken}` },
    });

  let response = await attempt();
  if (response.status === 401) {
    await refresh(session);
    response = await attempt();
  }
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

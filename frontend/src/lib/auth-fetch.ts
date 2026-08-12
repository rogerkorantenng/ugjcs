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

/** Node's `fetch` (undici) requires `duplex: "half"` to send a `ReadableStream` request
 * body, but `lib.dom.d.ts` does not declare that field on `RequestInit` — this local
 * extension is the typed alternative to an `any` cast or a `@ts-expect-error`. */
type StreamingRequestInit = RequestInit & { duplex?: "half" };

/**
 * The streaming counterpart to `authedFetch`, used only for multipart file uploads
 * (`POST /manuscripts`, `POST /manuscripts/{trackingCode}/resubmit`). The incoming Route
 * Handler's `request.body` is piped straight through as `init.body` rather than being
 * read into a buffer first, so this process never holds a full manuscript PDF in memory.
 *
 * A streamed body can only be consumed once, so — unlike `authedFetch` — there is no
 * reactive retry-on-401 here: buffering the body to allow a replay would defeat the point
 * of streaming it through in the first place. The proactive refresh below (identical to
 * `authedFetch`'s) is this path's only defence against a token that expires mid-upload.
 */
export async function authedFetchStream<T>(
  path: string,
  init: { method: string; body: ReadableStream<Uint8Array> | null; contentType: string },
): Promise<T> {
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

  const response = await fetch(`${env.API_BASE_URL}${path}`, {
    method: init.method,
    headers: { Authorization: `Bearer ${session.accessToken}`, "Content-Type": init.contentType },
    body: init.body,
    duplex: "half",
  } as StreamingRequestInit);
  if (!response.ok) throw new ProblemDetailsError(await toProblem(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

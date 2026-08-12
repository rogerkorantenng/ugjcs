import "server-only";
import { cookies } from "next/headers";
import { getIronSession, type IronSession, type SessionOptions } from "iron-session";
import { env } from "@/lib/env";
import type { SessionUser } from "@/types/api";

export interface SessionData {
  user?: SessionUser;
  accessToken?: string;
  refreshToken?: string;
  accessTokenExpiresAt?: number; // epoch millis
}

export const sessionOptions: SessionOptions = {
  cookieName: "ugjcs_session",
  password: env.SESSION_SECRET,
  cookieOptions: {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // matches the backend's 7-day refresh token lifetime (Plan 3)
  },
};

/** Only callable from a Route Handler, Server Action, or (read-only) a Server Component. */
export async function getSession(): Promise<IronSession<SessionData>> {
  return getIronSession<SessionData>(await cookies(), sessionOptions);
}

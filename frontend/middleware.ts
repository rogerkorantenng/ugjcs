import { NextResponse, type NextRequest } from "next/server";
import { getIronSession } from "iron-session";
import { sessionOptions, type SessionData } from "@/lib/session";
import type { Role } from "@/types/api";

const ROLE_BY_PREFIX: Record<string, Role> = {
  "/author": "author",
  "/reviewer": "reviewer",
  "/editor": "editor",
};

export async function middleware(request: NextRequest) {
  const prefix = Object.keys(ROLE_BY_PREFIX).find((p) => request.nextUrl.pathname.startsWith(p));
  if (!prefix) return NextResponse.next();

  const response = NextResponse.next();
  const session = await getIronSession<SessionData>(request, response, sessionOptions);
  const requiredRole = ROLE_BY_PREFIX[prefix];

  if (!session.user) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  if (!session.user.roles.includes(requiredRole) && !session.user.roles.includes("editor_in_chief")) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return response;
}

export const config = { matcher: ["/author/:path*", "/reviewer/:path*", "/editor/:path*"] };

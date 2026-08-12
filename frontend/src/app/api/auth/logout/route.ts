import { NextResponse } from "next/server";
import { env } from "@/lib/env";
import { getSession } from "@/lib/session";

export async function POST() {
  const session = await getSession();
  if (session.refreshToken) {
    await fetch(`${env.API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    }).catch(() => undefined); // best-effort revoke upstream; the cookie is destroyed regardless
  }
  session.destroy();
  return new NextResponse(null, { status: 204 });
}

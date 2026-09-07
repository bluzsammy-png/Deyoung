import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { OAUTH_STATE_COOKIE, googleAuthorizeUrl, googleConfigured, makeOAuthState } from "@/lib/users";

function originOf(req: Request): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/$/, "");
  const url = new URL(req.url);
  const proto = req.headers.get("x-forwarded-proto") ?? url.protocol.replace(":", "");
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? url.host;
  return `${proto}://${host}`;
}

/** W2: start Google OAuth. Honest failure when the owner has not configured credentials yet. */
export async function GET(req: Request) {
  if (!googleConfigured()) {
    return NextResponse.redirect(
      new URL("/#/signin?error=google_unconfigured", originOf(req))
    );
  }
  const state = makeOAuthState();
  const jar = await cookies();
  jar.set(OAUTH_STATE_COOKIE, state, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 600,
  });
  return NextResponse.redirect(googleAuthorizeUrl(originOf(req), state));
}

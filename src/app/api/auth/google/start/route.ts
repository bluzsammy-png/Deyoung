import { NextResponse } from "next/server";
import {
  GOOGLE_AUTH_URL, GOOGLE_NEXT_COOKIE, GOOGLE_STATE_COOKIE, googleConfigured, newState,
  originOf, redirectUri, safeNextPath,
} from "@/lib/google";

export const dynamic = "force-dynamic";

/**
 * GET /api/auth/google/start - begin Google Sign-In.
 * Sets a short-lived httpOnly state cookie (CSRF guard) and redirects to
 * Google's consent screen. If the operator has not configured credentials
 * yet, the user is simply returned to the studio - the button is hidden
 * in that case, this is a safety net.
 */
export async function GET(req: Request) {
  const origin = originOf(req);
  const url = new URL(req.url);
  // Where to land after consent - e.g. the subscribe flow that started the sign-up.
  const next = safeNextPath(url.searchParams.get("next")) || "/#studio";
  const back = NextResponse.redirect(`${origin}${next}`);

  if (!googleConfigured()) return back;

  const state = newState();
  const auth = new URL(GOOGLE_AUTH_URL);
  auth.searchParams.set("client_id", process.env.GOOGLE_CLIENT_ID || "");
  auth.searchParams.set("redirect_uri", redirectUri(req));
  auth.searchParams.set("response_type", "code");
  auth.searchParams.set("scope", "openid email profile");
  auth.searchParams.set("state", state);
  auth.searchParams.set("prompt", "select_account");

  const res = NextResponse.redirect(auth.toString());
  res.cookies.set(GOOGLE_STATE_COOKIE, state, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 600, // 10 minutes to complete consent
  });
  res.cookies.set(GOOGLE_NEXT_COOKIE, encodeURIComponent(next), {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 600,
  });
  return res;
}

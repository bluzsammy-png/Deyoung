import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createSession } from "@/lib/auth";
import {
  OAUTH_STATE_COOKIE,
  createUserSession,
  googleExchange,
  isAdminEmail,
  upsertGoogleUser,
  verifyOAuthState,
} from "@/lib/users";

function originOf(req: Request): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/$/, "");
  const url = new URL(req.url);
  const proto = req.headers.get("x-forwarded-proto") ?? url.protocol.replace(":", "");
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? url.host;
  return `${proto}://${host}`;
}

/**
 * W2: Google OAuth callback — verify state, upsert the user, enforce status,
 * hand out sessions. Allowlisted emails (ADMIN_EMAILS, default
 * deyoungsltd@gmail.com) get an ADMIN session too — that is the owner's
 * passwordless login.
 */
export async function GET(req: Request) {
  const origin = originOf(req);
  const url = new URL(req.url);
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const jar = await cookies();
  const cookieState = jar.get(OAUTH_STATE_COOKIE)?.value ?? "";
  jar.delete(OAUTH_STATE_COOKIE);

  if (!code || !state || !cookieState || state !== cookieState || !verifyOAuthState(state)) {
    return NextResponse.redirect(new URL("/#/signin?error=google_state", origin));
  }
  const profile = await googleExchange(code, origin);
  if (!profile || !profile.email || profile.email_verified === false) {
    return NextResponse.redirect(new URL("/#/signin?error=google_exchange", origin));
  }
  const user = await upsertGoogleUser(profile);
  if (user.status !== "active") {
    const reason = user.status === "banned" ? user.banReason || "Policy violation" : "Account deactivated";
    return NextResponse.redirect(
      new URL(`/#/signin?error=${encodeURIComponent(`Account ${user.status}: ${reason}`)}`, origin)
    );
  }
  await createUserSession(user);
  if (isAdminEmail(user.email)) {
    const admin = await (await import("@/lib/db")).db.admin.findUnique({ where: { email: user.email } });
    if (admin) await createSession(admin);
  }
  return NextResponse.redirect(new URL(isAdminEmail(user.email) ? "/#/admin" : "/#/dashboard", origin));
}

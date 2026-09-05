import crypto from "node:crypto";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { createUserSession } from "@/lib/auth";
import {
  GOOGLE_NEXT_COOKIE, GOOGLE_STATE_COOKIE, exchangeCodeForProfile, googleConfigured,
  originOf, redirectUri, safeNextPath,
} from "@/lib/google";

export const dynamic = "force-dynamic";

/**
 * GET /api/auth/google/callback - finish Google Sign-In.
 *
 * Security rules applied here:
 *   1. state cookie must match the ?state parameter (CSRF);
 *   2. the Google account's email must be verified by Google;
 *   3. linking into an existing password account happens ONLY for verified
 *      emails - an unverified email can never take over an account;
 *   4. Google-only accounts get passwordHash "google-oauth", which no
 *      password login path can verify (scrypt never matches that literal).
 */
export async function GET(req: Request) {
  const origin = originOf(req);
  const url = new URL(req.url);
  const code = url.searchParams.get("code") || "";
  const state = url.searchParams.get("state") || "";
  const stateCookie = req.headers
    .get("cookie")
    ?.split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${GOOGLE_STATE_COOKIE}=`))
    ?.split("=")[1] || "";

  const fail = (reason: string) =>
    NextResponse.redirect(`${origin}/?google_error=${encodeURIComponent(reason)}#studio`);

  // Post-consent destination (the subscribe flow sets this when the sign-up
  // started from checkout). Same-site paths only, validated in safeNextPath.
  const nextCookie = req.headers
    .get("cookie")
    ?.split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${GOOGLE_NEXT_COOKIE}=`))
    ?.split("=")[1] || "";
  const next = safeNextPath(decodeURIComponent(nextCookie)) || "/#studio";
  const done = () => {
    const res = NextResponse.redirect(`${origin}${next}`);
    res.cookies.delete(GOOGLE_NEXT_COOKIE);
    return res;
  };

  if (!googleConfigured()) return fail("unconfigured");
  if (!code || !state || !stateCookie || state !== stateCookie) return fail("state");

  try {
    const profile = await exchangeCodeForProfile(code, redirectUri(req));

    // already linked?
    const linked = await db.user.findFirst({ where: { googleId: profile.sub } });
    if (linked) {
      await createUserSession(linked);
      return done();
    }

    const existing = await db.user.findUnique({ where: { email: profile.email } });
    if (existing) {
      if (!profile.emailVerified) {
        return fail("unverified");
      }
      // Verified Google email matches an existing account → link it.
      await db.user.update({
        where: { id: existing.id },
        data: {
          googleId: profile.sub,
          avatarUrl: existing.avatarUrl || profile.picture,
        },
      });
      await createUserSession(existing);
      return done();
    }

    // Brand-new Google customer.
    const created = await db.user.create({
      data: {
        email: profile.email,
        name: profile.name || profile.email.split("@")[0],
        // No password exists for this account. The literal is never a valid
        // scrypt hash, so password login / change-password stay impossible
        // unless the user sets one later.
        passwordHash: `google-oauth$${crypto.randomBytes(16).toString("hex")}`,
        googleId: profile.sub,
        avatarUrl: profile.picture,
      },
    });
    await createUserSession(created);
    return done();
  } catch (e) {
    console.error("google callback failed", e);
    return fail("exchange");
  }
}

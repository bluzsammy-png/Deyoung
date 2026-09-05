import "server-only";
import crypto from "crypto";

/**
 * Google Sign-In (OAuth 2.0 / OpenID Connect) - server-side helpers.
 *
 * Real endpoints only (Google's discovery documents):
 *   authorize: https://accounts.google.com/o/oauth2/v2/auth
 *   token:     https://oauth2.googleapis.com/token
 *   userinfo:  https://openidconnect.googleapis.com/v1/userinfo
 *
 * The operator enables this by setting two environment variables on Railway:
 *   GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET  (Google Cloud → OAuth client,
 *   type "Web application", redirect URI: <site>/api/auth/google/callback)
 * Until then the product hides the Google button and the start route
 * redirects back - nothing is faked.
 */

export const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
export const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
export const GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo";
export const GOOGLE_STATE_COOKIE = "dy_g_state";
export const GOOGLE_NEXT_COOKIE = "dy_g_next";

/** Only same-site hash paths are allowed as post-login destinations. */
export function safeNextPath(raw: string | null): string | null {
  if (!raw) return null;
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.includes("://")) return null;
  return raw.slice(0, 200);
}

export function googleConfigured(): boolean {
  return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}

/** Public origin of this deployment (Railway terminates TLS, forwards host). */
export function originOf(req: Request): string {
  const host = req.headers.get("x-forwarded-host") || req.headers.get("host") || new URL(req.url).host;
  const proto = req.headers.get("x-forwarded-proto") || (host.startsWith("localhost") || host.startsWith("127.") ? "http" : "https");
  return `${proto}://${host}`;
}

export function redirectUri(req: Request): string {
  return `${originOf(req)}/api/auth/google/callback`;
}

export function newState(): string {
  return crypto.randomBytes(24).toString("hex");
}

export type GoogleProfile = {
  sub: string;
  email: string;
  emailVerified: boolean;
  name: string;
  picture: string;
};

/** Exchange an authorization code for tokens, then fetch verified profile claims. */
export async function exchangeCodeForProfile(
  code: string,
  redirectUriValue: string,
): Promise<GoogleProfile> {
  const res = await fetch(GOOGLE_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID || "",
      client_secret: process.env.GOOGLE_CLIENT_SECRET || "",
      redirect_uri: redirectUriValue,
      grant_type: "authorization_code",
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`token exchange failed (${res.status})`);
  }
  const tokens = (await res.json()) as { access_token?: string };
  if (!tokens.access_token) throw new Error("no access token from Google");

  const ui = await fetch(GOOGLE_USERINFO_URL, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
    cache: "no-store",
  });
  if (!ui.ok) throw new Error(`userinfo failed (${ui.status})`);
  const p = (await ui.json()) as {
    sub?: string; email?: string; email_verified?: boolean; name?: string; picture?: string;
  };
  if (!p.sub || !p.email) throw new Error("Google profile incomplete");
  return {
    sub: p.sub,
    email: p.email.toLowerCase(),
    emailVerified: p.email_verified === true,
    name: p.name || "",
    picture: p.picture || "",
  };
}

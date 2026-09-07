import "server-only";
import crypto from "crypto";
import { cookies } from "next/headers";
import { db } from "@/lib/db";
import {
  hashPassword,
  verifyPassword,
  signToken,
  authSecret,
  SESSION_TTL_SEC,
} from "@/lib/auth";

/**
 * W2 (Task 42) — site-user auth: credentials + Google OAuth, role/status gates,
 * owner-admin seeding. Admin sessions stay on the `dy_admin` cookie (see
 * auth.ts); user sessions live on `dy_user`, so the owner can hold BOTH at once
 * and no existing admin route changes behavior.
 */

export const USER_COOKIE = "dy_user";
export const OAUTH_STATE_COOKIE = "dy_oauth_state";
export const OAUTH_STATE_TTL_SEC = 10 * 60;

/** Comma-separated allowlist; any Google login with one of these emails is promoted to admin. */
export function adminEmails(): string[] {
  return (process.env.ADMIN_EMAILS ?? "deyoungsltd@gmail.com")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

export function isAdminEmail(email: string): boolean {
  return adminEmails().includes(email.trim().toLowerCase());
}

/* ---------- user sessions (same HMAC scheme as admin, role=user) ---------- */

function signUserToken(payload: { sub: string; email: string; exp: number }): string {
  return signToken({ ...payload, role: "user" });
}

export async function createUserSession(user: { id: string; email: string }): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const token = signUserToken({ sub: user.id, email: user.email, exp: now + SESSION_TTL_SEC });
  const jar = await cookies();
  jar.set(USER_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SEC,
  });
  return token;
}

export async function destroyUserSession(): Promise<void> {
  const jar = await cookies();
  jar.delete(USER_COOKIE);
}

export type UserSession =
  | { kind: "anon" }
  | { kind: "blocked"; status: string; reason: string; email: string }
  | {
      kind: "ok";
      user: {
        id: string;
        email: string;
        name: string;
        image: string;
        role: string;
        status: string;
        provider: string;
      };
    };

/** Load the signed-in site user and enforce status. Fail closed on banned/deactivated. */
export async function getUserSession(): Promise<UserSession> {
  const jar = await cookies();
  const token = jar.get(USER_COOKIE)?.value;
  if (!token) return { kind: "anon" };
  const { verifyToken } = await import("@/lib/auth");
  const payload = verifyToken(token);
  if (!payload || payload.role !== "user") return { kind: "anon" };
  const user = await db.user.findUnique({ where: { id: payload.sub } });
  if (!user) return { kind: "anon" };
  if (user.status !== "active") {
    return {
      kind: "blocked",
      status: user.status,
      reason: user.banReason,
      email: user.email,
    };
  }
  return {
    kind: "ok",
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
      image: user.image,
      role: user.role,
      status: user.status,
      provider: user.provider,
    },
  };
}

/* ---------- account creation / lookup ---------- */

export async function findUserByEmail(email: string) {
  return db.user.findUnique({ where: { email: email.trim().toLowerCase() } });
}

export async function createUser(input: {
  email: string;
  name?: string;
  password?: string;
  provider?: string;
  googleId?: string;
  image?: string;
}) {
  const email = input.email.trim().toLowerCase();
  const admin = isAdminEmail(email);
  return db.user.create({
    data: {
      email,
      name: input.name?.trim() ?? "",
      passwordHash: input.password ? hashPassword(input.password) : null,
      provider: input.provider ?? "credentials",
      googleId: input.googleId ?? null,
      image: input.image ?? "",
      role: admin ? "admin" : "user",
    },
  });
}

export async function verifyUserPassword(email: string, password: string) {
  const user = await findUserByEmail(email);
  if (!user || !user.passwordHash) return null;
  if (!verifyPassword(password, user.passwordHash)) return null;
  return user;
}

/**
 * Owner-admin seeding (idempotent, runs from the seed script and the auth
 * login route boot path): guarantees every address in ADMIN_EMAILS has an
 * Admin row so /admin login + Google promotion always work.
 */
export async function ensureOwnerAdmins(): Promise<void> {
  for (const email of adminEmails()) {
    const existing = await db.admin.findUnique({ where: { email } });
    if (existing) continue;
    const env = process.env.ADMIN_BOOTSTRAP_PASSWORD;
    const password = env && env.length >= 10 ? env : crypto.randomBytes(12).toString("base64url");
    await db.admin.create({ data: { email, passwordHash: hashPassword(password) } });
    if (!env) {
      console.log(`[admin-bootstrap] owner admin created — email: ${email} password: ${password} (change it in Security immediately)`);
    }
  }
}

/* ---------- Google OAuth (manual flow — one session system, no NextAuth) ---------- */

export function googleConfigured(): boolean {
  return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}

export function googleAuthorizeUrl(origin: string, state: string): string {
  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID ?? "",
    redirect_uri: `${origin}/api/auth/google/callback`,
    response_type: "code",
    scope: "openid email profile",
    state,
    prompt: "select_account",
    access_type: "online",
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

/** HMAC-signed state so the callback can reject forged/late flows without a DB table. */
export function makeOAuthState(): string {
  const body = Buffer.from(
    JSON.stringify({ n: crypto.randomBytes(12).toString("hex"), t: Date.now() })
  ).toString("base64url");
  const sig = crypto.createHmac("sha256", authSecret()).update(body).digest("base64url");
  return `${body}.${sig}`;
}

export function verifyOAuthState(state: string): boolean {
  try {
    const [body, sig] = state.split(".");
    if (!body || !sig) return false;
    const expected = crypto.createHmac("sha256", authSecret()).update(body).digest("base64url");
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;
    const data = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as { t: number };
    return Date.now() - data.t < OAUTH_STATE_TTL_SEC * 1000;
  } catch {
    return false;
  }
}

export interface GoogleProfile {
  sub: string;
  email: string;
  email_verified?: boolean;
  name?: string;
  picture?: string;
}

/** Exchange the OAuth code for tokens and fetch the verified profile. */
export async function googleExchange(code: string, origin: string): Promise<GoogleProfile | null> {
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID ?? "",
      client_secret: process.env.GOOGLE_CLIENT_SECRET ?? "",
      redirect_uri: `${origin}/api/auth/google/callback`,
      grant_type: "authorization_code",
    }),
  });
  if (!res.ok) return null;
  const tokens = (await res.json()) as { access_token?: string };
  if (!tokens.access_token) return null;
  const info = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
    headers: { authorization: `Bearer ${tokens.access_token}` },
  });
  if (!info.ok) return null;
  return (await info.json()) as GoogleProfile;
}

/** Upsert a Google login into a User (and Admin row when the email is allowlisted). */
export async function upsertGoogleUser(profile: GoogleProfile) {
  const email = profile.email.trim().toLowerCase();
  let user = await findUserByEmail(email);
  if (user) {
    user = await db.user.update({
      where: { id: user.id },
      data: {
        googleId: profile.sub,
        provider: user.passwordHash ? user.provider : "google",
        image: profile.picture ?? user.image,
        name: user.name || (profile.name ?? ""),
        lastLoginAt: new Date(),
      },
    });
  } else {
    user = await createUser({
      email,
      name: profile.name ?? "",
      provider: "google",
      googleId: profile.sub,
      image: profile.picture ?? "",
    });
    await db.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } });
  }
  if (isAdminEmail(email)) {
    await ensureOwnerAdmins();
    if (user.role !== "admin") {
      user = await db.user.update({ where: { id: user.id }, data: { role: "admin" } });
    }
  }
  return user;
}

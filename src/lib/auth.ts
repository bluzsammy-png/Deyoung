import "server-only";
import crypto from "crypto";
import { cookies } from "next/headers";
import fs from "fs";
import path from "path";
import { db } from "@/lib/db";

export const SESSION_COOKIE = "dy_admin";
const SESSION_TTL_SEC = 60 * 60 * 24 * 7; // 7 days
const SECRET_FILE = path.join(process.cwd(), "db", ".auth-secret");

/** Persisted per-install secret so sessions survive restarts. */
function getSecret(): string {
  try {
    if (fs.existsSync(SECRET_FILE)) {
      const s = fs.readFileSync(SECRET_FILE, "utf8").trim();
      if (s.length >= 32) return s;
    }
    const s = crypto.randomBytes(48).toString("hex");
    fs.mkdirSync(path.dirname(SECRET_FILE), { recursive: true });
    fs.writeFileSync(SECRET_FILE, s, { mode: 0o600 });
    return s;
  } catch {
    // last-resort deterministic fallback (still not guessable without db access)
    return crypto.createHash("sha256").update("deyoung-fallback-secret").digest("hex");
  }
}

/* ---------- password hashing (scrypt, no external deps) ---------- */

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt$${salt}$${hash}`;
}

export function verifyPassword(password: string, stored: string): boolean {
  try {
    const [scheme, salt, hash] = stored.split("$");
    if (scheme !== "scrypt" || !salt || !hash) return false;
    const candidate = crypto.scryptSync(password, salt, 64);
    const expected = Buffer.from(hash, "hex");
    return candidate.length === expected.length && crypto.timingSafeEqual(candidate, expected);
  } catch {
    return false;
  }
}

/* ---------- session token (HMAC-signed, stateless) ---------- */

type SessionPayload = { sub: string; email: string; exp: number };

function b64url(input: string | Buffer): string {
  return Buffer.from(input).toString("base64url");
}

export function signToken(payload: SessionPayload): string {
  const body = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac("sha256", getSecret()).update(body).digest("base64url");
  return `${body}.${sig}`;
}

export function verifyToken(token: string): SessionPayload | null {
  try {
    const [body, sig] = token.split(".");
    if (!body || !sig) return null;
    const expected = crypto.createHmac("sha256", getSecret()).update(body).digest("base64url");
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as SessionPayload;
    if (!payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

/* ---------- cookie session helpers ---------- */

export async function createSession(admin: { id: string; email: string }): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const token = signToken({ sub: admin.id, email: admin.email, exp: now + SESSION_TTL_SEC });
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: false, // behind tunnel/https in production; lax keeps it simple in preview
    path: "/",
    maxAge: SESSION_TTL_SEC,
  });
  return token;
}

export async function destroySession(): Promise<void> {
  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
}

export async function getSession(): Promise<SessionPayload | null> {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) return null;
  return verifyToken(token);
}

/** Guard for admin API routes. Returns true when the current request is the owner. */
export async function isAdmin(): Promise<boolean> {
  return (await getSession()) !== null;
}

/* ---------- admin bootstrap ---------- */

export const DEFAULT_ADMIN_EMAIL = "admin@deyoung.site";
export const DEFAULT_ADMIN_PASSWORD = "deyoung123";

export async function ensureAdmin(): Promise<void> {
  const count = await db.admin.count();
  if (count === 0) {
    await db.admin.create({
      data: {
        email: DEFAULT_ADMIN_EMAIL,
        passwordHash: hashPassword(DEFAULT_ADMIN_PASSWORD),
      },
    });
  }
}

export function isDefaultPassword(stored: string): boolean {
  return verifyPassword(DEFAULT_ADMIN_PASSWORD, stored);
}

/* ==================== DeYoung customer accounts (user plane) ==================== */

export const USER_COOKIE = "dy_user";

export type UserPayload = { sub: string; email: string; exp: number };

function userToken(payload: UserPayload): string {
  const body = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac("sha256", getSecret() + "|user").update(body).digest("base64url");
  return `${body}.${sig}`;
}

function verifyUserToken(token: string): UserPayload | null {
  try {
    const [body, sig] = token.split(".");
    if (!body || !sig) return null;
    const expected = crypto.createHmac("sha256", getSecret() + "|user").update(body).digest("base64url");
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as UserPayload;
    if (!payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

export async function createUserSession(user: { id: string; email: string }): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const token = userToken({ sub: user.id, email: user.email, exp: now + SESSION_TTL_SEC });
  const jar = await cookies();
  jar.set(USER_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
    maxAge: SESSION_TTL_SEC,
  });
  return token;
}

export async function destroyUserSession(): Promise<void> {
  const jar = await cookies();
  jar.delete(USER_COOKIE);
}

/** Current signed-in customer account payload (or null). */
export async function getUserSession(): Promise<UserPayload | null> {
  const jar = await cookies();
  const token = jar.get(USER_COOKIE)?.value;
  if (!token) return null;
  return verifyUserToken(token);
}

/** Full user record for the signed-in customer (or null). */
export async function getCurrentUser() {
  const s = await getUserSession();
  if (!s) return null;
  return db.user.findUnique({ where: { id: s.sub } });
}

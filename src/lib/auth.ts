import "server-only";
import crypto from "crypto";
import { cookies } from "next/headers";
import fs from "fs";
import path from "path";
import { db } from "@/lib/db";

export const SESSION_COOKIE = "dy_admin";
export const SESSION_TTL_SEC = 60 * 60 * 24 * 7; // 7 days
const SECRET_FILE = path.join(process.cwd(), "db", ".auth-secret");

/** Persisted per-install secret so sessions survive restarts. */
export function authSecret(): string {
  return getSecret();
}

function getSecret(): string {
  // W0 fix (C-3/§F.1): never fall back to a public deterministic value — that let
  // anyone forge admin sessions. Order: env → per-install file → fail closed.
  const env = process.env.AUTH_SECRET;
  if (env && env.length >= 32) return env;
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
    throw new Error(
      "AUTH_SECRET env var must be set (>=32 chars) when the filesystem is not writable — refusing to run with a guessable session secret"
    );
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

// W2 (Task 42): role added. Legacy tokens (no role) predate user accounts —
// isAdmin() falls back to checking the Admin table for those.
type SessionPayload = { sub: string; email: string; exp: number; role?: "admin" | "user" };

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
  const token = signToken({
    sub: admin.id,
    email: admin.email,
    exp: now + SESSION_TTL_SEC,
    role: "admin",
  });
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    // W0 fix (§F.1): HTTPS-only cookie in production (site is always behind TLS on
    // Railway/custom domain); plain HTTP localhost dev keeps working.
    secure: process.env.NODE_ENV === "production",
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
  const s = await getSession();
  if (!s) return false;
  if (s.role === "user") return false; // user sessions must never pass admin guards
  if (s.role === "admin") return true;
  // legacy token without a role claim — confirm the account is still an Admin row
  const row = await db.admin.findFirst({
    where: { OR: [{ id: s.sub }, { email: s.email.toLowerCase() }] },
    select: { id: true },
  });
  return row !== null;
}

/* ---------- admin bootstrap ---------- */

export const DEFAULT_ADMIN_EMAIL = "admin@deyoung.site";

/**
 * W0 fix (§F.1): the old hardcoded "deyoung123" bootstrap password was public in the
 * repo. Bootstrap password now comes from ADMIN_BOOTSTRAP_PASSWORD env, or is
 * generated randomly and printed ONCE to the server log on first boot.
 */
function bootstrapPassword(): string | null {
  const env = process.env.ADMIN_BOOTSTRAP_PASSWORD;
  if (env && env.length >= 10) return env;
  return null;
}

export async function ensureAdmin(): Promise<void> {
  const count = await db.admin.count();
  if (count === 0) {
    const fromEnv = bootstrapPassword();
    const password = fromEnv ?? crypto.randomBytes(12).toString("base64url");
    await db.admin.create({
      data: {
        email: DEFAULT_ADMIN_EMAIL,
        passwordHash: hashPassword(password),
      },
    });
    if (!fromEnv) {
      // shown once in deploy logs so the owner can claim the account, then change it
      console.log(
        `[admin-bootstrap] first admin created — email: ${DEFAULT_ADMIN_EMAIL} password: ${password} (change it in Security immediately)`
      );
    }
  }
}

export function isDefaultPassword(stored: string): boolean {
  // only "default" when the operator opted into an env bootstrap password
  const fromEnv = bootstrapPassword();
  return fromEnv !== null && verifyPassword(fromEnv, stored);
}

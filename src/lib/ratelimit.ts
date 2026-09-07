import "server-only";
import { db } from "@/lib/db";

/**
 * Rate limiting (spec §F.2) — W1 upgrade: Postgres-backed fixed-window counters.
 *
 * W0 shipped the §F.2 limits/keys/429 behavior as in-memory counters; W1 moves
 * the counters into the `RateLimit` table so they survive restarts, work across
 * instances, and are inspectable by the admin Security panel. The in-memory
 * engine is kept strictly as a FALLBACK: if the DB is unreachable (cold dev
 * sqlite, migration lag, brief provider outage) limiting degrades to
 * single-instance memory instead of failing every request open.
 *
 * Limits (per IP + route class):
 *   login 5/15min · code 3/10min · booking/subscription/contact 5/h ·
 *   video-request 10/h · verify 10/h · stream 120/min
 *
 * Concurrency note: find-then-update is not atomic; at this scale the worst
 * case is a couple of extra requests slipping through one window — acceptable,
 * and identical to the W0 semantics.
 */

type Window = { count: number; resetAt: number };

const memory = new Map<string, Window>();
let lastMemPrune = 0;
let lastRowPrune = 0;

export const LIMITS = {
  login: { max: 5, windowSec: 15 * 60 },
  signup: { max: 5, windowSec: 15 * 60 }, // W2: user registration
  ai: { max: 30, windowSec: 60 * 60 }, // W2: studio AI (enhance/script) calls
  code: { max: 3, windowSec: 10 * 60 },
  submit: { max: 5, windowSec: 60 * 60 }, // booking / subscription / contact
  request: { max: 10, windowSec: 60 * 60 }, // video render requests
  verify: { max: 10, windowSec: 60 * 60 },
  stream: { max: 120, windowSec: 60 },
  premiere: { max: 5, windowSec: 60 * 60 }, // W2.2: user premiere requests
} as const;

export type LimitClass = keyof typeof LIMITS;

export function clientIp(req: Request): string {
  const xf = req.headers.get("x-forwarded-for");
  if (xf) return xf.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

/* ----------------------------- memory fallback ----------------------------- */

function memoryRateLimit(
  key: string,
  max: number,
  windowSec: number
): { ok: true } | { ok: false; retryAfter: number } {
  const now = Date.now();
  if (now - lastMemPrune > 60_000) {
    lastMemPrune = now;
    for (const [k, w] of memory) if (w.resetAt <= now) memory.delete(k);
  }
  const w = memory.get(key);
  if (!w || w.resetAt <= now) {
    memory.set(key, { count: 1, resetAt: now + windowSec * 1000 });
    return { ok: true };
  }
  w.count += 1;
  if (w.count > max) {
    return { ok: false, retryAfter: Math.max(1, Math.ceil((w.resetAt - now) / 1000)) };
  }
  return { ok: true };
}

/* ------------------------------ postgres path ------------------------------ */

async function dbRateLimit(
  key: string,
  max: number,
  windowSec: number
): Promise<{ ok: true } | { ok: false; retryAfter: number }> {
  const now = Date.now();
  const existing = await db.rateLimit.findUnique({ where: { bucket: key } });

  if (!existing || existing.resetAt.getTime() <= now) {
    const resetAt = new Date(now + windowSec * 1000);
    // upsert covers the both-expired and brand-new cases (incl. races)
    await db.rateLimit.upsert({
      where: { bucket: key },
      create: { bucket: key, count: 1, resetAt },
      update: { count: 1, resetAt },
    });
    return { ok: true };
  }

  const count = existing.count + 1;
  await db.rateLimit.update({ where: { bucket: key }, data: { count } });
  if (count > max) {
    return { ok: false, retryAfter: Math.max(1, Math.ceil((existing.resetAt.getTime() - now) / 1000)) };
  }
  return { ok: true };
}

/** Opportunistic cleanup: rows whose window closed >24h ago are dead weight. */
async function pruneRows(): Promise<void> {
  const now = Date.now();
  if (now - lastRowPrune < 5 * 60_000) return;
  lastRowPrune = now;
  await db.rateLimit
    .deleteMany({ where: { resetAt: { lt: new Date(now - 24 * 60 * 60 * 1000) } } })
    .catch(() => undefined);
}

export async function rateLimit(
  req: Request,
  cls: LimitClass
): Promise<{ ok: true } | { ok: false; retryAfter: number }> {
  const { max, windowSec } = LIMITS[cls];
  const key = `${cls}:${clientIp(req)}`;
  try {
    const r = await dbRateLimit(key, max, windowSec);
    void pruneRows();
    return r;
  } catch (e) {
    // DB limiter unavailable — degrade to memory, never break the request path.
    console.warn(
      "[ratelimit] DB counters unavailable, using in-memory fallback:",
      e instanceof Error ? e.message : e
    );
    return memoryRateLimit(key, max, windowSec);
  }
}

export function tooMany(retryAfter: number): Response {
  return new Response(JSON.stringify({ ok: false, error: "Too many requests — slow down" }), {
    status: 429,
    headers: { "content-type": "application/json", "retry-after": String(retryAfter) },
  });
}

/** One-liner guard for route handlers: returns a 429 Response when limited, else null. */
export async function guard(req: Request, cls: LimitClass): Promise<Response | null> {
  const r = await rateLimit(req, cls);
  return r.ok ? null : tooMany(r.retryAfter);
}

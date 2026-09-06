import "server-only";

/**
 * Rate limiting — W0 fix (H-1/H-5, spec §F.2).
 *
 * v1: in-memory fixed-window counters (single Railway instance at current scale).
 * The spec's Postgres-backed `RateLimit` table upgrade lands in W1; the limits,
 * keys, and 429+Retry-After behavior below already match §F.2 exactly.
 *
 * Limits (per IP + route class):
 *   login 5/15min · code 3/10min · booking/subscription/contact 5/h ·
 *   video-request 10/h · verify 10/h · stream 120/min
 */

type Window = { count: number; resetAt: number };

const buckets = new Map<string, Window>();
let lastPrune = 0;

export const LIMITS = {
  login: { max: 5, windowSec: 15 * 60 },
  code: { max: 3, windowSec: 10 * 60 },
  submit: { max: 5, windowSec: 60 * 60 }, // booking / subscription / contact
  request: { max: 10, windowSec: 60 * 60 }, // video render requests
  verify: { max: 10, windowSec: 60 * 60 },
  stream: { max: 120, windowSec: 60 },
} as const;

export type LimitClass = keyof typeof LIMITS;

export function clientIp(req: Request): string {
  const xf = req.headers.get("x-forwarded-for");
  if (xf) return xf.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

function prune(now: number) {
  if (now - lastPrune < 60_000) return;
  lastPrune = now;
  for (const [k, w] of buckets) if (w.resetAt <= now) buckets.delete(k);
}

export function rateLimit(req: Request, cls: LimitClass): { ok: true } | { ok: false; retryAfter: number } {
  const { max, windowSec } = LIMITS[cls];
  const now = Date.now();
  prune(now);
  const key = `${cls}:${clientIp(req)}`;
  const w = buckets.get(key);
  if (!w || w.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + windowSec * 1000 });
    return { ok: true };
  }
  w.count += 1;
  if (w.count > max) {
    return { ok: false, retryAfter: Math.max(1, Math.ceil((w.resetAt - now) / 1000)) };
  }
  return { ok: true };
}

export function tooMany(retryAfter: number): Response {
  return new Response(JSON.stringify({ ok: false, error: "Too many requests — slow down" }), {
    status: 429,
    headers: { "content-type": "application/json", "retry-after": String(retryAfter) },
  });
}

/** One-liner guard for route handlers: returns a 429 Response when limited, else null. */
export function guard(req: Request, cls: LimitClass): Response | null {
  const r = rateLimit(req, cls);
  return r.ok ? null : tooMany(r.retryAfter);
}

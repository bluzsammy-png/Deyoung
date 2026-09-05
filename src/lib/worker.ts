import "server-only";
import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { bad } from "@/lib/api";

/**
 * PATI worker-plane auth.
 *
 * External render workers (Kaggle GPU kernels, the owner's PC, any GPU box)
 * authenticate with a single shared secret carried as `Authorization: Bearer <token>`.
 * The token lives in the WORKER_TOKEN env var on the server and is baked into the
 * worker / Kaggle kernel at launch time. It is intentionally separate from the
 * owner's admin session so a fleet of headless workers can run unattended.
 */
export function workerToken(): string {
  return (process.env.WORKER_TOKEN || "").trim();
}

/** Returns a response when the caller is not a valid worker, otherwise null. */
export function guardWorker(req: Request): NextResponse | null {
  const expected = workerToken();
  if (expected.length < 16) {
    return bad("Worker API is disabled - set WORKER_TOKEN (32+ chars) on the server first", 503);
  }
  const header = req.headers.get("authorization") || "";
  const bearer = header.startsWith("Bearer ") ? header.slice(7) : header;
  const provided = bearer.trim() || new URL(req.url).searchParams.get("token") || "";
  if (
    provided.length !== expected.length ||
    !timingSafeEqual(Buffer.from(provided), Buffer.from(expected))
  ) {
    return bad("Invalid worker token", 401);
  }
  return null;
}

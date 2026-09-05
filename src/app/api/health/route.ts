import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * Lightweight deploy healthcheck (Railway probes this before switching traffic).
 * Returns 200 only when the process is up AND the database answers a trivial query.
 * Kept deliberately cheap - one SELECT 1 with a short timeout, no content queries.
 */
export async function GET() {
  const started = Date.now();
  try {
    await Promise.race([
      db.$queryRawUnsafe("SELECT 1"),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("db ping timeout")), 3000)
      ),
    ]);
    return NextResponse.json(
      { ok: true, db: true, ms: Date.now() - started },
      { headers: { "cache-control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { ok: false, db: false, ms: Date.now() - started },
      { status: 503, headers: { "cache-control": "no-store" } }
    );
  }
}

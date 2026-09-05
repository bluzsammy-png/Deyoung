import { db } from "@/lib/db";
import { ok } from "@/lib/api";
import { guardWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

/**
 * GET /api/worker/status - heartbeat for render workers.
 * Lets a Kaggle kernel or local worker decide to keep polling, and gives the
 * owner a one-call view of the render fleet's workload.
 */
export async function GET(req: Request) {
  const denied = await guardWorker(req);
  if (denied) return denied;

  const [queued, rendering, done, failed] = await Promise.all([
    db.videoRequest.count({ where: { status: "queued" } }),
    db.videoRequest.count({ where: { status: "rendering" } }),
    db.videoRequest.count({ where: { status: "done" } }),
    db.videoRequest.count({ where: { status: "failed" } }),
  ]);

  return ok({ ok: true, queue: { queued, rendering, done, failed }, time: new Date().toISOString() });
}

import { db } from "@/lib/db";
import { bad, ok } from "@/lib/api";
import { guardWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

/**
 * GET /api/worker/jobs?status=failed|queued|rendering — worker-plane queue
 * visibility (Task 64).
 *
 * The claim endpoint only serves queued rows, so a fleet operator could never
 * SEE what was stuck. This list endpoint gives the plane (with the same
 * WORKER_TOKEN auth) a bounded, latest-first view of non-done rows so orphaned
 * renders can be identified and requeued via PATCH action=requeue. Same trust
 * level as claim: prompts are already exposed there.
 */
export async function GET(req: Request) {
  const denied = await guardWorker(req);
  if (denied) return denied;

  const status = new URL(req.url).searchParams.get("status") || "failed";
  if (!["failed", "queued", "rendering"].includes(status)) {
    return bad("status must be failed | queued | rendering", 400);
  }

  const jobs = await db.videoRequest.findMany({
    where: { status },
    orderBy: { createdAt: "desc" },
    take: 20,
    select: {
      id: true,
      prompt: true,
      seconds: true,
      resolution: true,
      status: true,
      notes: true,
      createdAt: true,
    },
  });

  return ok({ jobs, count: jobs.length });
}

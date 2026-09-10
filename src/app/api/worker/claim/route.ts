import { db } from "@/lib/db";
import { bad, ok } from "@/lib/api";
import { guardWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

/**
 * POST /api/worker/claim — a PATI-style render worker asks for the next job.
 *
 * Ordering mirrors queuePositionFor() exactly: queuePriority desc → createdAt
 * asc → id asc, so the queue position a customer sees is the order workers
 * actually pull. The queued → rendering transition is atomic (updateMany
 * guarded on status) so a fleet of concurrent workers can never double-claim.
 */
export async function POST(req: Request) {
  const denied = await guardWorker(req);
  if (denied) return denied;

  const body = await req.json().catch(() => ({}));
  const agent =
    (typeof body?.agent === "string" ? body.agent.trim().slice(0, 60) : "") || "unnamed-worker";

  // Reaper: a worker that dies mid-render leaves its row stuck in
  // "rendering" forever and the queue silently clogs. No heartbeat system
  // exists yet, so use the one hard signal we have: a legitimate render
  // never exceeds the worker-side hard cap (~35 min watchdog + upload
  // headroom). Past that, orphan the row honestly so the customer's queue
  // position math stays truthful.
  await db.videoRequest.updateMany({
    where: { status: "rendering", updatedAt: { lt: new Date(Date.now() - 45 * 60 * 1000) } },
    data: {
      status: "failed",
      notes: "orphaned: no worker reported back for 45+ minutes (worker died mid-render) — safe to re-submit",
    },
  });

  for (let attempt = 0; attempt < 5; attempt++) {
    const next = await db.videoRequest.findFirst({
      // rows whose notes contain "reserved:" are held back from automated
      // claimers — they exist to test a specific pipeline (e.g. the
      // Wav2Lip lip-sync E2E) and must not be drained by a plain renderer
      where: { status: "queued", notes: { not: { contains: "reserved:" } } },
      orderBy: [{ queuePriority: "desc" }, { createdAt: "asc" }, { id: "asc" }],
    });
    if (!next) {
      return ok({ job: null, message: "Queue is empty — check back soon." });
    }

    const claimed = await db.videoRequest.updateMany({
      where: { id: next.id, status: "queued" },
      data: { status: "rendering", notes: `claimed by ${agent} at ${new Date().toISOString()}` },
    });

    if (claimed.count === 1) {
      return ok({
        agent,
        job: {
          id: next.id,
          prompt: next.prompt,
          seconds: next.seconds,
          resolution: next.resolution,
          withAudio: next.withAudio,
          watermark: next.watermark,
          queuePriority: next.queuePriority,
          createdAt: next.createdAt,
        },
      });
    }
    // Another worker claimed this one in the split second between find and
    // update — loop and try the next job in the queue.
  }

  return bad("Could not claim a job this cycle — try again", 409);
}

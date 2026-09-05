import { db } from "@/lib/db";
import { bad, ok } from "@/lib/api";
import { guardWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

/**
 * POST /api/worker/claim - a PATI-style render worker asks for the next job.
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

  for (let attempt = 0; attempt < 5; attempt++) {
    const next = await db.videoRequest.findFirst({
      where: { status: "queued" },
      orderBy: [{ queuePriority: "desc" }, { createdAt: "asc" }, { id: "asc" }],
    });
    if (!next) {
      return ok({ job: null, message: "Queue is empty - check back soon." });
    }

    const claimed = await db.videoRequest.updateMany({
      where: { id: next.id, status: "queued" },
      data: { status: "rendering", progress: 0, stage: "claimed", notes: `claimed by ${agent} at ${new Date().toISOString()}` },
    });

    if (claimed.count === 1) {
      // Voice handoff: when the job uses a licensed clone, workers get the
      // voiceprint asset (and the label) so a voice-capable renderer can
      // speak with it. Unlicensed/revoked clones can never reach the queue -
      // submission is gated - so this lookup is a pass-through resolution.
      let voiceName = next.voice;
      let voiceSampleUrl = "";
      if (next.voice.startsWith("clone:")) {
        const vc = await db.voiceClone.findFirst({
          where: { id: next.voice.slice(6), status: "licensed" },
        });
        if (vc) {
          voiceName = vc.label;
          voiceSampleUrl = vc.sampleUrl;
        } else {
          voiceName = ""; // license vanished (revoked) - render silent rather than unlicensed
        }
      }

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
          model: next.model,
          voice: next.voice,
          voiceName,
          voiceSampleUrl,
          refImageUrl: next.refImageUrl,
          createdAt: next.createdAt,
        },
      });
    }
    // Another worker claimed this one in the split second between find and
    // update - loop and try the next job in the queue.
  }

  return bad("Could not claim a job this cycle - try again", 409);
}

import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";
import {
  RESOLUTION_RANK,
  activeSubForEmail,
  dedupKeyFor,
  estimateGpuMinutes,
  etaDaysFor,
  periodUsage,
  queuePositionFor,
  usageWindowStart,
} from "@/lib/subs";

/**
 * Public POST: submit a video request against an active subscription.
 * All tier limits are enforced server-side - the browser is never trusted.
 * Admin GET: the full render queue.
 */
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const email = str(body.email, 200).toLowerCase();
  const prompt = str(body.prompt, 4000);
  const seconds = Math.round(num(body.seconds));
  const resolution = str(body.resolution, 10) || "720p";
  const withAudio = Boolean(body.withAudio);

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("Enter the email you subscribed with");
  if (prompt.length < 5) return bad("Describe your video in a bit more detail");
  if (!RESOLUTION_RANK[resolution]) return bad("Unsupported resolution");

  const sub = await activeSubForEmail(email);
  if (!sub) {
    return bad("No active subscription found for this email - subscribe first, then submit videos.", 403);
  }

  const plan = await db.plan.findUnique({ where: { code: sub.planCode } });
  if (!plan) return bad("Your plan could not be loaded - contact the owner", 500);

  // ---- tier limits (server-side) ----
  if (seconds < 5) return bad("Videos start at 5 seconds");
  if (seconds > plan.maxSecondsVideo) {
    return bad(
      `Your ${plan.name} plan renders up to ${plan.maxSecondsVideo}s per video. Upgrade to go longer - up to 60 seconds in one pass.`,
      403
    );
  }
  if (RESOLUTION_RANK[resolution] > (RESOLUTION_RANK[plan.maxResolution] ?? 2)) {
    return bad(`Your ${plan.name} plan renders at ${plan.maxResolution} max.`, 403);
  }
  if (withAudio && !plan.audio) {
    return bad(`Audio is included from the Pro plan upward. Your ${plan.name} plan renders without audio.`, 403);
  }

  // ---- monthly quota ----
  const used = await periodUsage(sub.id, usageWindowStart(sub));
  if (used >= plan.maxVideosMonth) {
    return bad(
      `You have used all ${plan.maxVideosMonth} videos of your ${plan.name} plan for this period. Upgrade or wait for the next cycle.`,
      429
    );
  }

  // ---- dedup: identical prompt+params already rendered → instant cache delivery ----
  // (checked before the concurrent limit - a cache hit needs no render slot)
  const key = dedupKeyFor(prompt, seconds, resolution, withAudio);
  const cached = await db.videoRequest.findFirst({
    where: { dedupKey: key, status: "done", resultUrl: { not: "" } },
    orderBy: { updatedAt: "desc" },
  });

  if (cached) {
    const hit = await db.videoRequest.create({
      data: {
        subscriptionId: sub.id,
        email,
        prompt,
        seconds,
        resolution,
        withAudio,
        watermark: plan.watermark,
        queuePriority: plan.queuePriority,
        status: "done",
        resultUrl: cached.resultUrl,
        gpuMinutes: 0,
        dedupKey: key,
        fromCache: true,
        notes: "Delivered from the render cache - no GPU time used.",
      },
    });
    return ok({ request: hit, queuePosition: 0, etaDays: 0, fromCache: true, usage: { used: used + 1, quota: plan.maxVideosMonth } }, 201);
  }

  // ---- concurrent render limit ----
  const inFlight = await db.videoRequest.count({
    where: { subscriptionId: sub.id, status: { in: ["queued", "rendering"] } },
  });
  if (inFlight >= plan.concurrentJobs) {
    return bad(
      `Your ${plan.name} plan allows ${plan.concurrentJobs} video${plan.concurrentJobs > 1 ? "s" : ""} in the queue at once. Wait for a render to finish, or upgrade for more parallel slots.`,
      429
    );
  }

  const created = await db.videoRequest.create({
    data: {
      subscriptionId: sub.id,
      email,
      prompt,
      seconds,
      resolution,
      withAudio,
      watermark: plan.watermark,
      queuePriority: plan.queuePriority,
      status: "queued",
      dedupKey: key,
    },
  });

  const queuePosition = await queuePositionFor(created);
  const etaDays = await etaDaysFor(estimateGpuMinutes(seconds, resolution));
  return ok(
    { request: created, queuePosition, etaDays, fromCache: false, usage: { used: used + 1, quota: plan.maxVideosMonth } },
    201
  );
}

export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const requests = await db.videoRequest.findMany({ orderBy: [{ queuePriority: "desc" }, { createdAt: "asc" }] });
  return ok({ requests });
}

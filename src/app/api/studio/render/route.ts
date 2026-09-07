import { db } from "@/lib/db";
import { bad, ok, num, str } from "@/lib/api";
import { guard } from "@/lib/ratelimit";
import { getStudioSession } from "@/lib/users";
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

const ADMIN_FREE_PLAN = "admin-free";

/**
 * W2: submit a render from the AI Film Studio.
 * - Regular users: same server-side tier limits as /api/requests (session email,
 *   active subscription required).
 * - Admins: FREE unlimited — a synthetic always-active "admin-free" subscription
 *   keeps the queue/worker contract intact while every limit is bypassed.
 */
export async function POST(req: Request) {
  const limited = await guard(req, "request");
  if (limited) return limited;
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  const body = await req.json().catch(() => ({}));
  const email = s.user.email;
  const prompt = str(body.prompt, 4000);
  const seconds = Math.round(num(body.seconds));
  const resolution = str(body.resolution, 10) || "720p";
  const withAudio = Boolean(body.withAudio);
  const projectId = str(body.projectId, 40);
  const sceneId = str(body.sceneId, 20);
  if (prompt.length < 5) return bad("Describe your video in a bit more detail");
  if (!RESOLUTION_RANK[resolution]) return bad("Unsupported resolution");

  let subId: string;
  let watermark = true;
  let queuePriority = 0;
  let quota: number | null = null;
  let used = 0;

  if (s.user.role === "admin") {
    const existing = await db.subscription.findFirst({
      where: { planCode: ADMIN_FREE_PLAN, email, status: "active" },
    });
    const sub =
      existing ??
      (await db.subscription.create({
        data: {
          name: "Owner (studio)",
          email,
          planCode: ADMIN_FREE_PLAN,
          status: "active",
          provider: "internal",
          notes: "Synthetic unlimited subscription for owner studio access — never billed.",
        },
      }));
    subId = sub.id;
    watermark = false;
    queuePriority = 100; // owner renders first
  } else {
    const sub = await activeSubForEmail(email);
    if (!sub) {
      return bad("Subscribe to a plan first — your render queue unlocks the moment you do.", 403);
    }
    const plan = await db.plan.findUnique({ where: { code: sub.planCode } });
    if (!plan) return bad("Your plan could not be loaded — contact the owner", 500);
    if (seconds < 5) return bad("Videos start at 5 seconds");
    if (seconds > plan.maxSecondsVideo) {
      return bad(
        `Your ${plan.name} plan renders up to ${plan.maxSecondsVideo}s per video. Upgrade to go longer — up to 60 seconds in one pass.`,
        403
      );
    }
    if (RESOLUTION_RANK[resolution] > (RESOLUTION_RANK[plan.maxResolution] ?? 2)) {
      return bad(`Your ${plan.name} plan renders at ${plan.maxResolution} max.`, 403);
    }
    if (withAudio && !plan.audio) {
      return bad(`Audio is included from the Pro plan upward. Your ${plan.name} plan renders without audio.`, 403);
    }
    used = await periodUsage(sub.id, usageWindowStart(sub));
    if (used >= plan.maxVideosMonth) {
      return bad(
        `You have used all ${plan.maxVideosMonth} videos of your ${plan.name} plan for this period. Upgrade or wait for the next cycle.`,
        429
      );
    }
    const inFlight = await db.videoRequest.count({
      where: { subscriptionId: sub.id, status: { in: ["queued", "rendering"] } },
    });
    if (inFlight >= plan.concurrentJobs) {
      return bad(
        `Your ${plan.name} plan allows ${plan.concurrentJobs} render${plan.concurrentJobs > 1 ? "s" : ""} in the queue at once. Wait for one to finish, or upgrade.`,
        429
      );
    }
    subId = sub.id;
    watermark = plan.watermark;
    queuePriority = plan.queuePriority;
    quota = plan.maxVideosMonth;
  }

  const key = dedupKeyFor(prompt, seconds, resolution, withAudio);
  const created = await db.videoRequest.create({
    data: {
      subscriptionId: subId,
      email,
      prompt,
      seconds,
      resolution,
      withAudio,
      watermark,
      queuePriority,
      status: "queued",
      dedupKey: key,
      notes: projectId ? `studio:${projectId}:${sceneId}` : "studio",
    },
  });
  const queuePosition = await queuePositionFor(created);
  const etaDays = await etaDaysFor(estimateGpuMinutes(seconds, resolution));
  return ok(
    { request: created, queuePosition, etaDays, usage: { used: used + 1, quota } },
    201
  );
}

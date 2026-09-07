import { db } from "@/lib/db";
import { bad, ok } from "@/lib/api";
import { getUserSession } from "@/lib/users";
import { activeSubForEmail, planByCode, periodUsage, usageWindowStart } from "@/lib/subs";

/**
 * W2: everything the user dashboard needs — account, subscription, plan,
 * GPU life (usage vs plan budget), recent render requests.
 * Admins get the same shape with unlimited:true and no subscription requirement.
 */
export async function GET() {
  const s = await getUserSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return ok({ blocked: { status: s.status, reason: s.reason } }, 200);

  const email = s.user.email;
  const isAdmin = s.user.role === "admin";
  const sub = await activeSubForEmail(email);
  const plan = sub ? await planByCode(sub.planCode) : null;

  let usage: {
    videosUsed: number;
    videosQuota: number | null;
    gpuMinutesUsed: number;
    gpuMinutesBudget: number | null;
    windowStart: string | null;
    resetAt: string | null;
  } = {
    videosUsed: 0,
    videosQuota: null,
    gpuMinutesUsed: 0,
    gpuMinutesBudget: null,
    windowStart: null,
    resetAt: null,
  };

  if (sub && plan) {
    const start = usageWindowStart(sub);
    const [videosUsed, agg] = await Promise.all([
      periodUsage(sub.id, sub.periodStart),
      db.videoRequest.aggregate({
        _sum: { gpuMinutes: true },
        where: { subscriptionId: sub.id, createdAt: { gte: start } },
      }),
    ]);
    // honest GPU budget for the plan: every allowed video at the plan's
    // resolution ceiling (1080p = 1 min/second of film, else 0.5)
    const factor = plan.maxResolution === "1080p" ? 1.0 : 0.5;
    usage = {
      videosUsed,
      videosQuota: plan.maxVideosMonth,
      gpuMinutesUsed: Math.round((agg._sum.gpuMinutes ?? 0) * 10) / 10,
      gpuMinutesBudget: Math.round(plan.maxVideosMonth * plan.maxSecondsVideo * factor),
      windowStart: start.toISOString(),
      resetAt: sub.periodEnd ? sub.periodEnd.toISOString() : null,
    };
  }

  const requests = await db.videoRequest.findMany({
    where: { email },
    orderBy: { createdAt: "desc" },
    take: 10,
    select: {
      id: true,
      prompt: true,
      seconds: true,
      resolution: true,
      status: true,
      resultUrl: true,
      gpuMinutes: true,
      createdAt: true,
    },
  });

  const projects = await db.studioProject.findMany({
    where: { userId: s.user.id },
    orderBy: { updatedAt: "desc" },
    take: 8,
    select: { id: true, title: true, niche: true, status: true, updatedAt: true },
  });

  return ok({
    user: s.user,
    unlimited: isAdmin,
    subscription: sub
      ? {
          id: sub.id,
          planCode: sub.planCode,
          status: sub.status,
          periodStart: sub.periodStart?.toISOString() ?? null,
          periodEnd: sub.periodEnd?.toISOString() ?? null,
        }
      : null,
    plan: plan
      ? {
          code: plan.code,
          name: plan.name,
          maxVideosMonth: plan.maxVideosMonth,
          maxSecondsVideo: plan.maxSecondsVideo,
          maxResolution: plan.maxResolution,
          watermark: plan.watermark,
          concurrentJobs: plan.concurrentJobs,
          queuePriority: plan.queuePriority,
          commercial: plan.commercial,
          audio: plan.audio,
        }
      : null,
    usage,
    requests,
    projects,
  });
}

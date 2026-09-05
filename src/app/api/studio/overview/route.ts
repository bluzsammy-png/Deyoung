import { db } from "@/lib/db";
import { bad, ok } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { DEYO_MODELS } from "@/lib/models";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);

  const sub = await db.subscription.findFirst({
    where: { email: user.email, status: "active", periodEnd: { gt: new Date() } },
    orderBy: { periodEnd: "desc" },
  });
  const plan = sub ? await db.plan.findUnique({ where: { code: sub.planCode } }) : null;

  // Honest engine telemetry, computed from the real queue history.
  const [queued, rendering, done24, avgRow] = await Promise.all([
    db.videoRequest.count({ where: { status: "queued" } }),
    db.videoRequest.count({ where: { status: "rendering" } }),
    db.videoRequest.count({
      where: { status: "done", updatedAt: { gte: new Date(Date.now() - 24 * 3600 * 1000) } },
    }),
    db.videoRequest.findMany({
      where: { status: "done", updatedAt: { gte: new Date(Date.now() - 7 * 24 * 3600 * 1000) } },
      select: { createdAt: true, updatedAt: true },
      take: 200,
      orderBy: { updatedAt: "desc" },
    }),
  ]);
  const avgRenderMin =
    avgRow.length > 0
      ? Math.round(
          (avgRow.reduce((acc, r) => acc + (r.updatedAt.getTime() - r.createdAt.getTime()), 0) / avgRow.length / 60000) * 10
        ) / 10
      : null;

  const used = sub
    ? await db.videoRequest.count({
        where: { subscriptionId: sub.id, createdAt: { gte: sub.periodStart ?? new Date(0) } },
      })
    : 0;

  return ok({
    models: DEYO_MODELS,
    engine: {
      queued,
      rendering,
      done24,
      avgRenderMin,
      gpuLaneOnline: rendering > 0 || done24 > 0, // workers reported activity recently
    },
    subscription: sub
      ? { id: sub.id, planCode: sub.planCode, status: sub.status, periodEnd: sub.periodEnd }
      : null,
    plan: plan
      ? {
          code: plan.code,
          name: plan.name,
          maxVideosMonth: plan.maxVideosMonth,
          maxSecondsVideo: plan.maxSecondsVideo,
          maxResolution: plan.maxResolution,
          queuePriority: plan.queuePriority,
          watermark: plan.watermark,
          audio: plan.audio,
        }
      : null,
    used,
    user: { id: user.id, email: user.email, name: user.name, avatarUrl: user.avatarUrl },
  });
}

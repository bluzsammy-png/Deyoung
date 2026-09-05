import crypto from "node:crypto";
import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { getModel } from "@/lib/models";

export const dynamic = "force-dynamic";

const VOICES = ["amara", "kossi", "zola", "dee", "narrator"];

/** Queue position for a queued request, using the exact order the worker claims in. */
async function queuePosition(req: { queuePriority: number; createdAt: Date; id: string }): Promise<number> {
  const ahead = await db.videoRequest.count({
    where: {
      status: "queued",
      OR: [
        { queuePriority: { gt: req.queuePriority } },
        {
          queuePriority: req.queuePriority,
          OR: [
            { createdAt: { lt: req.createdAt } },
            { createdAt: req.createdAt, id: { lt: req.id } },
          ],
        },
      ],
    },
  });
  return ahead + 1;
}

export async function GET() {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);

  const rows = await db.videoRequest.findMany({
    where: { OR: [{ userId: user.id }, { email: user.email }] },
    orderBy: [{ queuePriority: "desc" }, { createdAt: "asc" }],
    take: 100,
  });

  const withPositions = await Promise.all(
    rows.map(async (r) => ({
      id: r.id,
      prompt: r.prompt,
      model: r.model,
      seconds: r.seconds,
      resolution: r.resolution,
      status: r.status,
      stage: r.stage,
      progress: r.progress,
      fromCache: r.fromCache,
      resultUrl: r.resultUrl,
      notes: r.notes,
      voice: r.voice,
      refImageUrl: r.refImageUrl,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      queuePosition: r.status === "queued" ? await queuePosition(r) : null,
    }))
  );
  return ok({ requests: withPositions, voices: VOICES });
}

export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);

  const body = await req.json().catch(() => ({}));
  const prompt = str(body.prompt, 4000).trim();
  const modelCode = str(body.model, 40) || "deyo.1";
  const voice = str(body.voice, 40);
  const refImageUrl = str(body.refImageUrl, 500);
  const model = getModel(modelCode);

  if (prompt.length < 10) return bad("Describe your video in at least 10 characters");

  // ---- voice licensing gate: a cloned voice must be a licensed, unrevoked
  // VoiceClone owned by THIS user. Stock voices are whitelisted. ----
  if (voice.startsWith("clone:")) {
    const vc = await db.voiceClone.findFirst({
      where: { id: voice.slice(6), userId: user.id, status: "licensed" },
    });
    if (!vc) {
      return bad("That voice license is not active - pick it from your licensed voices or contact support", 403);
    }
  } else if (voice && !VOICES.includes(voice)) {
    return bad("Unknown voice - pick one from the list", 400);
  }

  // ---- entitlement: an active subscription drives every limit ----
  const sub = await db.subscription.findFirst({
    where: { email: user.email, status: "active", periodEnd: { gt: new Date() } },
    orderBy: { periodEnd: "desc" },
  });
  if (!sub) {
    return bad("You need an active subscription to render. Pick a plan first - your rate stays locked while you stay subscribed.", 402);
  }
  const plan = await db.plan.findUnique({ where: { code: sub.planCode } });
  if (!plan) return bad("Subscription plan not found - contact support", 500);

  const used = await db.videoRequest.count({
    where: { subscriptionId: sub.id, createdAt: { gte: sub.periodStart ?? new Date(0) } },
  });
  if (used >= plan.maxVideosMonth) {
    return bad(`Your ${plan.name} plan includes ${plan.maxVideosMonth} videos this period - used ${used}. Upgrade or wait for the next period.`, 402);
  }

  const seconds = Math.max(5, Math.min(model.secondsCap, plan.maxSecondsVideo, Number(body.seconds) || 15));
  const resolution = plan.maxResolution === "1080p" ? (body.resolution === "1080p" ? "1080p" : "720p") : "720p";
  const withAudio = plan.audio && (body.withAudio === true || model.tier !== "free");

  const dedupKey = crypto.createHash("sha256").update(`${prompt}|${seconds}|${resolution}|${withAudio}|${model.code}|${voice}`).digest("hex");

  // identical request already delivered? deliver instantly from cache
  const cached = await db.videoRequest.findFirst({
    where: { dedupKey, status: "done", resultUrl: { not: "" } },
    orderBy: { updatedAt: "desc" },
  });

  const created = await db.videoRequest.create({
    data: {
      subscriptionId: sub.id,
      email: user.email,
      userId: user.id,
      prompt,
      seconds,
      resolution,
      withAudio,
      watermark: plan.watermark,
      queuePriority: plan.queuePriority + model.queuePriority,
      model: model.code,
      voice,
      refImageUrl,
      dedupKey,
      fromCache: !!cached,
      status: cached ? "done" : "queued",
      resultUrl: cached ? cached.resultUrl : "",
      notes: cached ? "Delivered instantly - identical render found in cache." : "",
      stage: cached ? "cache hit" : "waiting for a worker",
    },
  });

  return ok({ request: { id: created.id, fromCache: created.fromCache, status: created.status } });
}

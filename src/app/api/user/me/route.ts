import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getCurrentUser, getUserSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

async function quotaFor(userId: string, email: string) {
  const sub = await db.subscription.findFirst({
    where: { email, status: "active", periodEnd: { gt: new Date() } },
    orderBy: { periodEnd: "desc" },
  });
  const plan = sub ? await db.plan.findUnique({ where: { code: sub.planCode } }) : null;
  let used = 0;
  if (sub) {
    used = await db.videoRequest.count({
      where: { OR: [{ userId }, { email }], subscriptionId: sub.id, createdAt: { gte: sub.periodStart ?? new Date(0) } },
    });
  }
  return {
    subscription: sub
      ? { id: sub.id, planCode: sub.planCode, status: sub.status, periodEnd: sub.periodEnd, pricePaid: sub.pricePaid, currency: sub.currency }
      : null,
    plan: plan
      ? { code: plan.code, name: plan.name, maxVideosMonth: plan.maxVideosMonth, maxSecondsVideo: plan.maxSecondsVideo, maxResolution: plan.maxResolution, queuePriority: plan.queuePriority, watermark: plan.watermark, audio: plan.audio }
      : null,
    used,
  };
}

export async function GET() {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const quota = await quotaFor(user.id, user.email);
  return ok({
    user: { id: user.id, email: user.email, name: user.name, phone: user.phone, avatarUrl: user.avatarUrl, createdAt: user.createdAt },
    ...quota,
  });
}

export async function PATCH(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const body = await req.json().catch(() => ({}));
  const name = body.name !== undefined ? str(body.name, 120).trim() : user.name;
  const phone = body.phone !== undefined ? str(body.phone, 40).trim() : user.phone;
  const avatarUrl = body.avatarUrl !== undefined ? str(body.avatarUrl, 500) : user.avatarUrl;
  if (body.name !== undefined && !name) return bad("Name cannot be empty");
  const updated = await db.user.update({ where: { id: user.id }, data: { name, phone, avatarUrl } });
  return ok({ user: { id: updated.id, email: updated.email, name: updated.name, phone: updated.phone, avatarUrl: updated.avatarUrl } });
}

/** Keep the session payload fresh after profile edits (email never changes here). */
export async function HEAD() {
  const s = await getUserSession();
  return new Response(null, { status: s ? 200 : 401 });
}

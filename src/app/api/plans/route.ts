import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";
import { isAdmin } from "@/lib/auth";

/** Public: list active plans for the pricing section (owner sees all, incl. inactive). */
export async function GET() {
  const owner = await isAdmin();
  const plans = await db.plan.findMany({
    where: owner ? {} : { active: true },
    orderBy: { sortOrder: "asc" },
  });
  return ok({ plans });
}

type PlanPatch = {
  code?: string;
  name?: string;
  blurb?: string;
  priceMonthly?: number;
  compareAtPrice?: number | null;
  currency?: string;
  maxVideosMonth?: number;
  maxSecondsVideo?: number;
  maxResolution?: string;
  watermark?: boolean;
  concurrentJobs?: number;
  queuePriority?: number;
  commercial?: boolean;
  audio?: boolean;
  featuresJson?: string;
  active?: boolean;
  sortOrder?: number;
};

export async function PUT(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") return bad("Invalid body");
  const updates = (body as { plans?: unknown }).plans;
  if (!Array.isArray(updates) || updates.length === 0) return bad("No plans supplied");

  for (const raw of updates as Record<string, unknown>[]) {
    const code = str(raw.code, 40);
    if (!code) return bad("Every plan needs its code");
    const existing = await db.plan.findUnique({ where: { code } });
    if (!existing) return bad(`Unknown plan: ${code}`);

    const maxResolution = ["480p", "720p", "1080p"].includes(str(raw.maxResolution, 10))
      ? str(raw.maxResolution, 10)
      : existing.maxResolution;

    const patch: PlanPatch = {
      name: raw.name !== undefined ? str(raw.name, 60) || existing.name : existing.name,
      blurb: raw.blurb !== undefined ? str(raw.blurb, 300) : existing.blurb,
      priceMonthly: raw.priceMonthly !== undefined ? Math.max(0, num(raw.priceMonthly)) : existing.priceMonthly,
      compareAtPrice:
        raw.compareAtPrice !== undefined
          ? raw.compareAtPrice === null || raw.compareAtPrice === ""
            ? null
            : Math.max(0, num(raw.compareAtPrice))
          : existing.compareAtPrice,
      currency: raw.currency !== undefined ? str(raw.currency, 8).toUpperCase() || existing.currency : existing.currency,
      maxVideosMonth:
        raw.maxVideosMonth !== undefined ? Math.min(1000, Math.max(1, Math.round(num(raw.maxVideosMonth)))) : existing.maxVideosMonth,
      maxSecondsVideo:
        raw.maxSecondsVideo !== undefined ? Math.min(600, Math.max(5, Math.round(num(raw.maxSecondsVideo)))) : existing.maxSecondsVideo,
      maxResolution,
      watermark: raw.watermark !== undefined ? Boolean(raw.watermark) : existing.watermark,
      concurrentJobs:
        raw.concurrentJobs !== undefined ? Math.min(10, Math.max(1, Math.round(num(raw.concurrentJobs)))) : existing.concurrentJobs,
      queuePriority:
        raw.queuePriority !== undefined ? Math.min(5, Math.max(0, Math.round(num(raw.queuePriority)))) : existing.queuePriority,
      commercial: raw.commercial !== undefined ? Boolean(raw.commercial) : existing.commercial,
      audio: raw.audio !== undefined ? Boolean(raw.audio) : existing.audio,
      featuresJson: raw.featuresJson !== undefined ? str(raw.featuresJson, 8000) || existing.featuresJson : existing.featuresJson,
      active: raw.active !== undefined ? Boolean(raw.active) : existing.active,
      sortOrder: raw.sortOrder !== undefined ? Math.round(num(raw.sortOrder)) : existing.sortOrder,
    };

    await db.plan.update({ where: { code }, data: patch });
  }

  const plans = await db.plan.findMany({ orderBy: { sortOrder: "asc" } });
  return ok({ plans });
}

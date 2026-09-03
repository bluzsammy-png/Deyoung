import "server-only";
import crypto from "crypto";
import { db } from "@/lib/db";
import type { Plan, Subscription } from "@prisma/client";

export const RESOLUTION_RANK: Record<string, number> = { "480p": 1, "720p": 2, "1080p": 3 };

/** Coarse GPU-minute estimate used for the honest ETA + capacity math. */
export function estimateGpuMinutes(seconds: number, resolution: string): number {
  const factor = resolution === "1080p" ? 1.0 : 0.5;
  return Math.max(1, Math.round(seconds * factor));
}

export function dedupKeyFor(prompt: string, seconds: number, resolution: string, audio: boolean): string {
  return crypto
    .createHash("sha256")
    .update(`${prompt.trim().toLowerCase()}|${seconds}|${resolution}|${audio ? "a" : "s"}`)
    .digest("hex");
}

/** The subscription that quota checks run against (latest active, not expired). */
export async function activeSubForEmail(email: string): Promise<Subscription | null> {
  const now = new Date();
  const sub = await db.subscription.findFirst({
    where: {
      email: { equals: email.trim().toLowerCase() },
      status: "active",
      OR: [{ periodEnd: null }, { periodEnd: { gt: now } }],
    },
    orderBy: { createdAt: "desc" },
  });
  return sub;
}

export async function planByCode(code: string): Promise<Plan | null> {
  return db.plan.findUnique({ where: { code } });
}

/** Videos used inside the subscription's current period. */
export async function periodUsage(subscriptionId: string, periodStart: Date | null): Promise<number> {
  return db.videoRequest.count({
    where: {
      subscriptionId,
      status: { in: ["queued", "rendering", "done"] },
      ...(periodStart ? { createdAt: { gte: periodStart } } : {}),
    },
  });
}

/**
 * 1-based position in the render queue: higher priority first, then FIFO.
 * Returns 0 when the request is not waiting anymore.
 */
export async function queuePositionFor(req: {
  id: string;
  queuePriority: number;
  createdAt: Date;
  status: string;
}): Promise<number> {
  if (req.status !== "queued" && req.status !== "rendering") return 0;
  const ahead = await db.videoRequest.count({
    where: {
      status: { in: ["queued", "rendering"] },
      OR: [
        { queuePriority: { gt: req.queuePriority } },
        {
          queuePriority: req.queuePriority,
          createdAt: { lt: req.createdAt },
        },
        {
          queuePriority: req.queuePriority,
          createdAt: req.createdAt,
          id: { lt: req.id },
        },
      ],
    },
  });
  return ahead + 1;
}

/** Days of backlog at the current daily GPU budget (rounded up, min 1). */
export async function etaDaysFor(gpuMinutesNeeded: number): Promise<number> {
  const s = await db.settings.findUnique({ where: { id: "main" } });
  const budget = Math.max(30, s?.gpuMinutesDaily ?? 240);
  return Math.max(1, Math.ceil(gpuMinutesNeeded / budget));
}

/** Start of the usage window for a subscription (its period start, or calendar month). */
export function usageWindowStart(sub: Subscription): Date {
  if (sub.periodStart) return sub.periodStart;
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

export function isSubActive(sub: Subscription): boolean {
  if (sub.status !== "active") return false;
  if (sub.periodEnd && sub.periodEnd.getTime() < Date.now()) return false;
  return true;
}

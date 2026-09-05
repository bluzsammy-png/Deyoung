import { db } from "@/lib/db";
import { guardAdmin, ok } from "@/lib/api";

/** Admin dashboard overview stats. */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const [bookings, pending, paid, confirmed, revenue, messages, unread, photos, services, subs, subsActive, subsPending, subsRevenue, queued, rendering, gpuToday, gpuBudgetRow, recent] =
    await Promise.all([
      db.booking.count(),
      db.booking.count({ where: { status: "pending" } }),
      db.booking.count({ where: { status: "paid" } }),
      db.booking.count({ where: { status: "confirmed" } }),
      db.booking.findMany({ where: { status: { in: ["paid", "confirmed"] } }, select: { amount: true, currency: true } }),
      db.message.count(),
      db.message.count({ where: { read: false } }),
      db.photo.count(),
      db.service.count({ where: { active: true } }),
      db.subscription.count(),
      db.subscription.count({ where: { status: "active" } }),
      db.subscription.count({ where: { status: "pending" } }),
      db.subscription.findMany({ where: { status: { in: ["active", "pending"] } }, select: { pricePaid: true, currency: true } }),
      db.videoRequest.count({ where: { status: "queued" } }),
      db.videoRequest.count({ where: { status: "rendering" } }),
      db.videoRequest.aggregate({ where: { status: "done", updatedAt: { gte: todayStart } }, _sum: { gpuMinutes: true } }),
      db.settings.findUnique({ where: { id: "main" }, select: { gpuMinutesDaily: true } }),
      db.booking.findMany({ orderBy: { createdAt: "desc" }, take: 5 }),
    ]);

  const total = revenue.reduce((sum, b) => sum + b.amount, 0);
  const currency = revenue[0]?.currency ?? "USD";
  const subsMrr = subsRevenue.reduce((sum, s) => sum + s.pricePaid, 0);

  return ok({
    stats: {
      bookings,
      pending,
      paid,
      confirmed,
      revenueTotal: Math.round(total * 100) / 100,
      currency,
      messages,
      unread,
      photos,
      activeServices: services,
      subscribers: subs,
      subscribersActive: subsActive,
      subscribersPending: subsPending,
      subsMrr: Math.round(subsMrr * 100) / 100,
      queueDepth: queued + rendering,
      gpuMinutesToday: Math.round((gpuToday._sum.gpuMinutes ?? 0) * 10) / 10,
      gpuMinutesBudget: gpuBudgetRow?.gpuMinutesDaily ?? 240,
    },
    recentBookings: recent,
  });
}

import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

/** Admin: activate / extend / cancel a subscription, or delete it. */
export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const { id } = await ctx.params;
  const sub = await db.subscription.findUnique({ where: { id } });
  if (!sub) return bad("Subscription not found", 404);

  const body = await req.json().catch(() => ({}));
  const action = str(body.action, 30);

  if (action === "activate") {
    const months = Math.min(24, Math.max(1, Math.round(num(body.months) || 1)));
    const base = sub.periodEnd && sub.periodEnd > new Date() ? sub.periodEnd : new Date();
    const periodEnd = new Date(base);
    periodEnd.setMonth(periodEnd.getMonth() + months);
    const updated = await db.subscription.update({
      where: { id },
      data: {
        status: "active",
        periodStart: sub.periodStart ?? new Date(),
        periodEnd,
        pricePaid: body.pricePaid !== undefined ? Math.max(0, num(body.pricePaid)) : sub.pricePaid,
        provider: str(body.provider, 30) || sub.provider,
        paymentRef: str(body.paymentRef, 200) || sub.paymentRef,
        notes: str(body.notes, 2000) || sub.notes,
      },
    });
    return ok({ subscription: updated });
  }

  if (action === "cancel") {
    const updated = await db.subscription.update({ where: { id }, data: { status: "cancelled" } });
    return ok({ subscription: updated });
  }

  if (action === "reactivate") {
    const updated = await db.subscription.update({ where: { id }, data: { status: "pending" } });
    return ok({ subscription: updated });
  }

  return bad("Unknown action - use activate, cancel or reactivate");
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const sub = await db.subscription.findUnique({ where: { id } });
  if (!sub) return bad("Subscription not found", 404);
  await db.videoRequest.deleteMany({ where: { subscriptionId: id } });
  await db.subscription.delete({ where: { id } });
  return ok({ deleted: true });
}

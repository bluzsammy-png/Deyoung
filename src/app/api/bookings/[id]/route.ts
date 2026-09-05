import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

const STATUSES = ["pending", "paid", "confirmed", "cancelled"];

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;

  const body = await req.json().catch(() => ({}));
  const data: Record<string, string> = {};
  if ("status" in body) {
    const status = str(body.status, 20);
    if (!STATUSES.includes(status)) return bad("Unknown status");
    data.status = status;
  }
  if ("notes" in body) data.notes = str(body.notes, 2000);
  if ("paymentRef" in body) data.paymentRef = str(body.paymentRef, 200);

  const booking = await db.booking.update({ where: { id }, data }).catch(() => null);
  if (!booking) return bad("Booking not found", 404);
  return ok({ booking });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.booking.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

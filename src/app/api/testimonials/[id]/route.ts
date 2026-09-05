import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const data: Record<string, string | number | boolean> = {};
  if ("name" in body) data.name = str(body.name, 120);
  if ("role" in body) data.role = str(body.role, 120);
  if ("quote" in body) data.quote = str(body.quote, 1000);
  if ("rating" in body) data.rating = Math.min(5, Math.max(1, parseInt(String(body.rating), 10) || 5));
  if ("active" in body) data.active = !!body.active;
  const t = await db.testimonial.update({ where: { id }, data }).catch(() => null);
  if (!t) return bad("Testimonial not found", 404);
  return ok({ testimonial: t });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.testimonial.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

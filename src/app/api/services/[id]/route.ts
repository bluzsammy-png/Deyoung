import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const data: Record<string, string | number | boolean | null> = {};
  if ("title" in body) data.title = str(body.title, 160);
  if ("description" in body) data.description = str(body.description, 2000);
  if ("price" in body) data.price = num(body.price);
  if ("compareAtPrice" in body)
    data.compareAtPrice = body.compareAtPrice === null || body.compareAtPrice === "" ? null : num(body.compareAtPrice);
  if ("duration" in body) data.duration = str(body.duration, 80);
  if ("active" in body) data.active = !!body.active;
  if ("sortOrder" in body) data.sortOrder = parseInt(String(body.sortOrder), 10) || 0;
  const service = await db.service.update({ where: { id }, data }).catch(() => null);
  if (!service) return bad("Service not found", 404);
  return ok({ service });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.service.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

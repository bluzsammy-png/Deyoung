import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const data: Record<string, string | number> = {};
  if ("title" in body) data.title = str(body.title, 160);
  if ("alt" in body) data.alt = str(body.alt, 300);
  if ("sortOrder" in body) data.sortOrder = parseInt(String(body.sortOrder), 10) || 0;
  const photo = await db.photo.update({ where: { id }, data }).catch(() => null);
  if (!photo) return bad("Photo not found", 404);
  return ok({ photo });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.photo.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

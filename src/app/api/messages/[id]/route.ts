import { db } from "@/lib/db";
import { guardAdmin, ok } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const m = await db.message.update({ where: { id }, data: { read: true } }).catch(() => null);
  if (!m) return ok({ deleted: true });
  return ok({ message: m });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.message.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const data: Record<string, string | number | boolean> = {};
  if ("question" in body) data.question = str(body.question, 300);
  if ("answer" in body) data.answer = str(body.answer, 3000);
  if ("active" in body) data.active = !!body.active;
  if ("sortOrder" in body) data.sortOrder = parseInt(String(body.sortOrder), 10) || 0;
  const faq = await db.faq.update({ where: { id }, data }).catch(() => null);
  if (!faq) return bad("FAQ not found", 404);
  return ok({ faq });
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  await db.faq.delete({ where: { id } }).catch(() => null);
  return ok({ deleted: true });
}

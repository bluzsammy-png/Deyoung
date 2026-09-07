import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";

export const dynamic = "force-dynamic";

const CATEGORIES = ["ai-film", "style-lab", "studio", "commercial"];
const STATUSES = ["pending", "published", "rejected"];

/**
 * PATCH /api/admin/premieres/:id — edit wall copy, feature/unfeature, or move a
 * premiere between pending | published | rejected. Every transition to or from
 * "published" keeps the underlying asset's isPublic flag honest: public on the
 * wall means public bytes, anything else means private again.
 */
export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const { id } = await ctx.params;
  const premiere = await db.premiere.findUnique({ where: { id } });
  if (!premiere) return bad("Premiere not found", 404);

  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return bad("Invalid body");
  }

  const data: {
    title?: string;
    logline?: string;
    category?: string;
    durationSec?: number;
    posterUrl?: string;
    featured?: boolean;
    status?: string;
  } = {};

  if ("title" in body) {
    const title = str(body.title, 120);
    if (!title) return bad("Title cannot be empty");
    data.title = title;
  }
  if ("logline" in body) data.logline = str(body.logline, 280);
  if ("category" in body) {
    const category = str(body.category, 40);
    if (!CATEGORIES.includes(category)) return bad("Pick a valid category");
    data.category = category;
  }
  if ("durationSec" in body) data.durationSec = Math.max(0, Math.round(num(body.durationSec)));
  if ("posterUrl" in body) data.posterUrl = str(body.posterUrl, 500);
  if ("featured" in body) data.featured = Boolean(body.featured);
  if ("status" in body) {
    const status = str(body.status, 20);
    if (!STATUSES.includes(status)) return bad("Invalid status");
    data.status = status;
  }

  const nextStatus = data.status ?? premiere.status;
  const updated = await db.premiere.update({ where: { id }, data });

  // Asset privacy follows the wall: publish → public, unpublish → private.
  if (premiere.assetId && nextStatus !== premiere.status) {
    await db.asset.update({
      where: { id: premiere.assetId },
      data: { isPublic: nextStatus === "published" },
    });
  }

  return ok({ premiere: { id: updated.id, status: updated.status } });
}

/** DELETE /api/admin/premieres/:id — remove from the wall entirely. */
export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const { id } = await ctx.params;
  const premiere = await db.premiere.findUnique({ where: { id } });
  if (!premiere) return bad("Premiere not found", 404);

  await db.premiere.delete({ where: { id } });
  // A deleted premiere never leaves its asset accidentally public.
  if (premiere.assetId && premiere.status === "published") {
    await db.asset.update({ where: { id: premiere.assetId }, data: { isPublic: false } });
  }
  return ok({ deleted: id });
}

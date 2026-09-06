import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";
import { queuePositionFor } from "@/lib/subs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * Public GET (with the submitter's email as the proof): status + queue position.
 * Admin PATCH: move through the render pipeline (start, deliver, fail, cancel).
 */
export async function GET(req: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const email = (new URL(req.url).searchParams.get("email") || "").trim().toLowerCase();
  if (!email) return bad("Email is required to check a request");

  const request = await db.videoRequest.findUnique({ where: { id } });
  if (!request || request.email !== email) return bad("Request not found", 404);

  const queuePosition = await queuePositionFor(request);
  // Internal /api/files delivery URLs are private-by-default; the id+email match
  // the customer just used IS the authorization — append it so the link works.
  const resultUrl =
    request.resultAssetId && request.resultUrl.startsWith("/api/files/")
      ? `${request.resultUrl}?request=${request.id}&email=${encodeURIComponent(email)}`
      : request.resultUrl;
  return ok({
    request: {
      id: request.id,
      prompt: request.prompt,
      seconds: request.seconds,
      resolution: request.resolution,
      status: request.status,
      resultUrl,
      fromCache: request.fromCache,
      createdAt: request.createdAt,
    },
    queuePosition,
  });
}

export async function PATCH(req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const { id } = await ctx.params;
  const request = await db.videoRequest.findUnique({ where: { id } });
  if (!request) return bad("Request not found", 404);

  const body = await req.json().catch(() => ({}));
  const action = str(body.action, 30);

  if (action === "start") {
    const updated = await db.videoRequest.update({ where: { id }, data: { status: "rendering" } });
    return ok({ request: updated });
  }

  if (action === "deliver") {
    const resultUrl = str(body.resultUrl, 500);
    if (!resultUrl) return bad("A result file URL is required to deliver");
    // admin-delivered internal assets (/api/files/:assetId) get linked for customer authz
    const m = /^\/api\/files\/([A-Za-z0-9_-]+)$/.exec(resultUrl);
    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "done",
        resultUrl,
        resultAssetId: m ? m[1] : request.resultAssetId,
        gpuMinutes: body.gpuMinutes !== undefined ? Math.max(0, num(body.gpuMinutes)) : request.gpuMinutes,
      },
    });
    return ok({ request: updated });
  }

  if (action === "fail") {
    const updated = await db.videoRequest.update({
      where: { id },
      data: { status: "failed", notes: str(body.notes, 2000) || request.notes },
    });
    return ok({ request: updated });
  }

  if (action === "cancel") {
    const updated = await db.videoRequest.update({ where: { id }, data: { status: "cancelled" } });
    return ok({ request: updated });
  }

  return bad("Unknown action — use start, deliver, fail or cancel");
}

export async function DELETE(_req: Request, ctx: Ctx) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const request = await db.videoRequest.findUnique({ where: { id } });
  if (!request) return bad("Request not found", 404);
  await db.videoRequest.delete({ where: { id } });
  return ok({ deleted: true });
}

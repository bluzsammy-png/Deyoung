import { promises as fs } from "node:fs";
import path from "node:path";
import { db } from "@/lib/db";
import { bad, num, ok, str } from "@/lib/api";
import { guardWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

const MAX_UPLOAD = 200 * 1024 * 1024; // matches the plan caps and Railway body limits

/**
 * PATCH /api/worker/jobs/:id - worker-side render pipeline transitions.
 *
 * - action=deliver (multipart): upload the finished mp4. Stored under
 *   public/uploads and served through /api/worker/file/:name so delivery works
 *   identically in dev and in the standalone production bundle.
 * - action=deliver (JSON): { resultUrl } for workers that host the file
 *   elsewhere (OSS bucket, transfer service).
 * - action=fail: put the job back in a visible "failed" state with a reason -
 *   the owner can requeue it from the admin Video Queue, and workers should
 *   fail honestly instead of looping forever on a poison prompt.
 * - action=progress: lightweight heartbeat note (optional).
 */
export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const denied = await guardWorker(req);
  if (denied) return denied;

  const { id } = await ctx.params;
  const request = await db.videoRequest.findUnique({ where: { id } });
  if (!request) return bad("Request not found", 404);
  if (["done", "cancelled"].includes(request.status)) {
    return bad(`Job is already ${request.status} - nothing to update`, 409);
  }

  const contentType = req.headers.get("content-type") || "";

  // ---------- multipart delivery (the normal path) ----------
  if (contentType.includes("multipart/form-data")) {
    const form = await req.formData().catch(() => null);
    if (!form) return bad("Bad multipart payload");

    if (String(form.get("action") || "deliver") !== "deliver") {
      return bad("Multipart updates only support action=deliver");
    }
    const file = form.get("file");
    if (!(file instanceof File)) return bad("A video file field named 'file' is required");
    if (file.size === 0 || file.size > MAX_UPLOAD) {
      return bad("Video must be between 1 byte and 200MB");
    }
    const gpuMinutes = num(form.get("gpuMinutes"));
    const renderer = (String(form.get("renderer") || "worker") + "").slice(0, 40);

    const dir = path.join(process.cwd(), "public", "uploads");
    await fs.mkdir(dir, { recursive: true });
    const name = `req-${id}.mp4`;
    await fs.writeFile(path.join(dir, name), Buffer.from(await file.arrayBuffer()));

    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "done",
        resultUrl: `/api/worker/file/${name}?v=1`,
        progress: 100,
        stage: "delivered",
        gpuMinutes: gpuMinutes > 0 ? gpuMinutes : request.gpuMinutes,
        fromCache: false,
        notes: `rendered by ${renderer} - delivered ${new Date().toISOString()}` +
          (form.get("qa") ? ` - ${String(form.get("qa")).slice(0, 200)}` : ""),
      },
    });
    return ok({
      request: { id: updated.id, status: updated.status, resultUrl: updated.resultUrl },
    });
  }

  // ---------- JSON actions ----------
  const body = await req.json().catch(() => ({}));
  const action = str(body.action, 20);

  if (action === "deliver") {
    const resultUrl = str(body.resultUrl, 500);
    if (!resultUrl) return bad("resultUrl is required for JSON delivery");
    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "done",
        resultUrl,
        gpuMinutes:
          body.gpuMinutes !== undefined ? Math.max(0, num(body.gpuMinutes)) : request.gpuMinutes,
        notes: str(body.notes, 500) || request.notes,
      },
    });
    return ok({
      request: { id: updated.id, status: updated.status, resultUrl: updated.resultUrl },
    });
  }

  if (action === "fail") {
    const agent = str(body.agent, 60) || "worker";
    const reason = str(body.notes, 1000) || "render failed";
    const updated = await db.videoRequest.update({
      where: { id },
      data: { status: "failed", notes: `${reason} - reported by ${agent} at ${new Date().toISOString()}` },
    });
    return ok({ request: { id: updated.id, status: updated.status } });
  }

  if (action === "progress") {
    const note = str(body.notes, 500);
    if (!note) return bad("A progress note is required");
    // Optional numeric progress 0-100 + short stage label - powers the user panel's live bar.
    const rawPct = Number(body.progress);
    const progress = Number.isFinite(rawPct) ? Math.max(0, Math.min(100, Math.round(rawPct))) : undefined;
    const stage = str(body.stage, 120);
    await db.videoRequest.update({
      where: { id },
      data: {
        notes: note.slice(0, 500),
        ...(progress !== undefined ? { progress, status: progress >= 100 ? "rendering" : "rendering" } : {}),
        ...(stage ? { stage } : {}),
      },
    });
    return ok({ request: { id } });
  }

  return bad("Unknown action - use deliver, fail or progress");
}

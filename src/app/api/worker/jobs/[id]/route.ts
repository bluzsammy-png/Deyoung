import { db } from "@/lib/db";
import { bad, num, ok, str } from "@/lib/api";
import { guardWorker } from "@/lib/worker";
import { buildKey, putObject, sha256, sniffMime } from "@/lib/storage";
import { sendRenderDoneEmail, sendRenderFailedEmail } from "@/lib/render-mail";

export const dynamic = "force-dynamic";

const MAX_UPLOAD = 200 * 1024 * 1024; // matches the plan caps and Railway body limits

/**
 * PATCH /api/worker/jobs/:id — worker-side render pipeline transitions.
 *
 * - action=deliver (multipart): upload the finished mp4. Stored in OBJECT
 *   STORAGE via the storage adapter (spec §D.1) with an Asset metadata row, and
 *   served through /api/files/:assetId — survives deploys forever (fixes C-4)
 *   and is private-by-default (fixes H-4).
 * - action=deliver (JSON): { resultUrl } for workers that host the file
 *   elsewhere (OSS bucket, transfer service).
 * - action=fail: put the job back in a visible "failed" state with a reason —
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
    return bad(`Job is already ${request.status} — nothing to update`, 409);
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

    // W1: object storage + Asset row (spec §D.1) — no more ephemeral public/uploads
    const buf = Buffer.from(await file.arrayBuffer());
    const sniffed = sniffMime(buf);
    if (!sniffed || sniffed.kind !== "video") {
      return bad(
        "Delivered file is not a recognizable video (MP4/WebM/MOV magic bytes required) — refusing to store it"
      );
    }
    let assetId: string;
    try {
      const key = buildKey("renders", `req-${id}.mp4`);
      const put = await putObject(key, buf, sniffed.mime);
      const asset = await db.asset.create({
        data: {
          kind: "video",
          mime: sniffed.mime,
          bytes: buf.length,
          storageKey: put.key,
          driver: put.driver,
          isPublic: false,
          sha256: sha256(buf),
          createdBy: `worker:${renderer}`,
        },
      });
      assetId = asset.id;
    } catch (e) {
      // honest failure — the worker can retry, nothing pretends success (prompt §65)
      return bad(e instanceof Error ? e.message : "Storage write failed", 503);
    }

    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "done",
        resultAssetId: assetId,
        resultUrl: `/api/files/${assetId}`,
        gpuMinutes: gpuMinutes > 0 ? gpuMinutes : request.gpuMinutes,
        fromCache: false,
        notes: `rendered by ${renderer} — delivered ${new Date().toISOString()}`,
      },
    });
    // Fire-and-forget: the customer learns their film is ready the moment the
    // GPU lands it. Never blocks or fails the delivery response.
    void sendRenderDoneEmail(updated);
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
    // link internal assets so the customer id+email authz on /api/files works
    const m = /^\/api\/files\/([A-Za-z0-9_-]+)$/.exec(resultUrl);
    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "done",
        resultAssetId: m ? m[1] : request.resultAssetId,
        resultUrl,
        gpuMinutes:
          body.gpuMinutes !== undefined ? Math.max(0, num(body.gpuMinutes)) : request.gpuMinutes,
        notes: str(body.notes, 500) || request.notes,
      },
    });
    void sendRenderDoneEmail(updated);
    return ok({
      request: { id: updated.id, status: updated.status, resultUrl: updated.resultUrl },
    });
  }

  if (action === "fail") {
    const agent = str(body.agent, 60) || "worker";
    const reason = str(body.notes, 1000) || "render failed";
    const updated = await db.videoRequest.update({
      where: { id },
      data: { status: "failed", notes: `${reason} — reported by ${agent} at ${new Date().toISOString()}` },
    });
    void sendRenderFailedEmail(updated, reason);
    return ok({ request: { id: updated.id, status: updated.status } });
  }

  if (action === "progress") {
    const note = str(body.notes, 500);
    if (!note) return bad("A progress note is required");
    await db.videoRequest.update({ where: { id }, data: { notes: note.slice(0, 500) } });
    return ok({ request: { id } });
  }

  // Task 64 — fleet self-repair: the 45-min orphan reaper honestly fails rows
  // whose worker died mid-render (sandbox rebuilds, studio freezes). Those rows
  // are SAFE to re-render (nothing was wrong with the request itself). A fleet
  // operator (WORKER_TOKEN) may requeue exactly that class of row — never
  // genuine render failures and never rows in any other state. The resulting
  // notes must not contain "reserved:" (which would hide it from claimers).
  if (action === "requeue") {
    if (request.status !== "failed") {
      return bad(`requeue only applies to failed rows — this one is ${request.status}`, 409);
    }
    if (!request.notes.includes("orphaned:")) {
      return bad("requeue is only for reaper-orphaned rows (notes must contain 'orphaned:') — genuine failures stay failed", 409);
    }
    const agent = str(body.agent, 60) || "worker";
    const updated = await db.videoRequest.update({
      where: { id },
      data: {
        status: "queued",
        notes: `requeued by ${agent} after orphan reap — ${new Date().toISOString()}`,
      },
    });
    return ok({ request: { id: updated.id, status: updated.status } });
  }

  return bad("Unknown action — use deliver, fail, progress or requeue");
}

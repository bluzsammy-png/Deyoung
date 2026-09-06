import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { db } from "@/lib/db";
import { bad } from "@/lib/api";
import { isAdmin } from "@/lib/auth";
import { currentDriver, objectStat, signedUrl } from "@/lib/storage";

export const dynamic = "force-dynamic";

/**
 * GET /api/files/:assetId — unified media delivery (spec §D.1).
 *
 * Replaces both the unauthenticated /api/worker/file/:name route (H-4) and the
 * fragile static /uploads path (C-4). Delivery strategy:
 *   - supabase driver → 302 to a 10-minute presigned URL (survives deploys,
 *     Range handled by the storage host).
 *   - local driver    → streamed here with Range support (dev convenience).
 *
 * Authorization: public assets (site imagery) are open; private assets
 * (renders, audio) require an admin session OR the customer id+email match
 * that the site already uses for request-status lookups (upgrade path to
 * per-request signed tokens lands with customer accounts, spec §B).
 */
export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const asset = await db.asset.findUnique({ where: { id } });
  if (!asset) return bad("Not found", 404);

  if (!asset.isPublic) {
    const admin = await isAdmin();
    if (!admin) {
      // customer path: ?request=<requestId>&email=<email> must match a request
      // whose result is exactly this asset (same trust model as /api/requests/[id])
      const url = new URL(req.url);
      const requestId = url.searchParams.get("request") || "";
      const email = (url.searchParams.get("email") || "").trim().toLowerCase();
      if (requestId && email) {
        const match = await db.videoRequest.findFirst({
          where: { id: requestId, email, resultAssetId: asset.id },
          select: { id: true },
        });
        if (!match) return bad("Not found", 404);
      } else {
        return bad("Not found", 404);
      }
    }
  }

  const driver = asset.driver === "supabase" ? "supabase" : currentDriver();

  if (driver === "supabase") {
    try {
      const target = await signedUrl(asset.storageKey, 600);
      if (target) {
        return new Response(null, {
          status: 302,
          headers: {
            Location: target,
            "Cache-Control": asset.isPublic
              ? "public, max-age=3600"
              : "private, no-store",
          },
        });
      }
      // supabase asset while driver switched to local — fall through to fetch
      const { getObject } = await import("@/lib/storage");
      const buf = await getObject(asset.storageKey);
      if (!buf) return bad("Media is unavailable — the storage driver changed or the object is gone", 410);
      return new Response(new Uint8Array(buf), {
        headers: {
          "Content-Type": asset.mime,
          "Content-Length": String(buf.length),
          "Cache-Control": "private, no-store",
        },
      });
    } catch (e) {
      return bad(e instanceof Error ? e.message : "Storage unavailable", 503);
    }
  }

  // local driver — stream with Range support (iOS Safari requires 206)
  const file = path.join(process.cwd(), "media", asset.storageKey);
  const info = await stat(file).catch(() => null);
  if (!info || !info.isFile()) return bad("Not found", 404);

  const size = info.size;
  const baseHeaders: Record<string, string> = {
    "Content-Type": asset.mime,
    "Accept-Ranges": "bytes",
    "Cache-Control": asset.isPublic
      ? "public, max-age=31536000, immutable"
      : "private, no-store",
    "Content-Disposition": asset.isPublic ? "inline" : "inline",
  };

  const range = req.headers.get("range");
  const match = range ? /bytes=(\d*)-(\d*)/.exec(range) : null;

  if (match) {
    let start = match[1] ? parseInt(match[1], 10) : 0;
    const end = match[2] ? Math.min(parseInt(match[2], 10), size - 1) : size - 1;
    if (!Number.isFinite(start) || start < 0) start = 0;
    if (start >= size) {
      return new Response(null, {
        status: 416,
        headers: { "Content-Range": `bytes */${size}` },
      });
    }
    const stream = createReadStream(file, { start, end });
    return new Response(Readable.toWeb(stream) as ReadableStream, {
      status: 206,
      headers: {
        ...baseHeaders,
        "Content-Range": `bytes ${start}-${end}/${size}`,
        "Content-Length": String(end - start + 1),
      },
    });
  }

  const stream = createReadStream(file);
  return new Response(Readable.toWeb(stream) as ReadableStream, {
    headers: { ...baseHeaders, "Content-Length": String(size) },
  });
}

/** Existence probe used by the admin UI to show real states instead of broken images. */
export async function HEAD(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const asset = await db.asset.findUnique({ where: { id }, select: { storageKey: true, driver: true } });
  if (!asset) return new Response(null, { status: 404 });
  const info = await objectStat(asset.storageKey);
  return new Response(null, { status: info ? 200 : 410 });
}

import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { bad } from "@/lib/api";

export const dynamic = "force-dynamic";

const DIR = path.join(process.cwd(), "public", "uploads");
const SAFE = /^[A-Za-z0-9._-]+$/;

/**
 * GET /api/worker/file/:name - stream a worker-delivered render.
 *
 * Range-capable (206) so <video> playback and download resumes work in every
 * browser, including iOS Safari which refuses progressive video without it.
 * The name is strictly whitelist-checked so this can never traverse paths.
 */
export async function GET(req: Request, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;
  if (!SAFE.test(name) || !name.endsWith(".mp4")) return bad("Not found", 404);

  const file = path.join(DIR, name);
  const info = await stat(file).catch(() => null);
  if (!info || !info.isFile()) return bad("Not found", 404);

  const size = info.size;
  const baseHeaders: Record<string, string> = {
    "Content-Type": "video/mp4",
    "Accept-Ranges": "bytes",
    "Cache-Control": "public, max-age=3600",
  };

  const range = req.headers.get("range");
  const match = range ? /bytes=(\d*)-(\d*)/.exec(range) : null;

  if (match) {
    let start = match[1] ? parseInt(match[1], 10) : 0;
    const end = match[2] ? Math.min(parseInt(match[2], 10), size - 1) : size - 1;
    if (!Number.isFinite(start) || start < 0) start = 0;
    if (start > end || start >= size) {
      return new Response(null, {
        status: 416,
        headers: { "Content-Range": `bytes */${size}` },
      });
    }
    const stream = Readable.toWeb(createReadStream(file, { start, end })) as ReadableStream;
    return new Response(stream, {
      status: 206,
      headers: {
        ...baseHeaders,
        "Content-Range": `bytes ${start}-${end}/${size}`,
        "Content-Length": String(end - start + 1),
      },
    });
  }

  const stream = Readable.toWeb(createReadStream(file)) as ReadableStream;
  return new Response(stream, {
    status: 200,
    headers: { ...baseHeaders, "Content-Length": String(size) },
  });
}

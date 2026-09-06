import { db } from "@/lib/db";
import { guardAdmin, bad, ok } from "@/lib/api";
import {
  buildKey,
  currentDriver,
  putObject,
  sha256,
  SIZE_CAPS,
  sniffMime,
} from "@/lib/storage";
import { guard } from "@/lib/ratelimit";

export const dynamic = "force-dynamic";

/**
 * POST /api/upload — admin media upload (fixes C-5, spec §E.6).
 *
 * multipart/form-data with one `file` field. The real type is decided by
 * magic bytes (never the client's content-type or filename), sizes are capped
 * per kind (image 8MB / video 200MB / audio 50MB), and bytes go straight to
 * object storage (spec §D.1) — never into the repo, public/, or Postgres.
 *
 * Returns { assetId, url } where url is the same-origin /api/files/:id delivery
 * path, which the existing admin UI (admin-content.tsx, admin-subs.tsx) already
 * expects.
 */
export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const limited = await guard(req, "submit");
  if (limited) return limited;

  const form = await req.formData().catch(() => null);
  if (!form) return bad("Bad multipart payload");
  const file = form.get("file");
  if (!(file instanceof File)) return bad("A file field is required");
  if (file.size === 0) return bad("Empty file");

  const buf = Buffer.from(await file.arrayBuffer());
  const sniffed = sniffMime(buf);
  if (!sniffed) {
    return bad(
      "Unsupported media type — accepted: JPEG, PNG, WebP, GIF images; MP4/WebM/MOV video; MP3/WAV/OGG audio"
    );
  }
  const cap = SIZE_CAPS[sniffed.kind];
  if (buf.length > cap) {
    return bad(
      `File is ${(buf.length / 1024 / 1024).toFixed(1)}MB — ${sniffed.kind} cap is ${cap / 1024 / 1024}MB`
    );
  }

  let driver: string;
  let key: string;
  try {
    driver = currentDriver();
    key = buildKey(
      sniffed.kind === "video" ? "renders" : sniffed.kind === "audio" ? "audio" : "site",
      `upload.${sniffed.ext}`
    );
    await putObject(key, buf, sniffed.mime);
  } catch (e) {
    // surfaces REQUIRES CONFIGURATION verbatim — honest states only (prompt §6)
    return bad(e instanceof Error ? e.message : "Storage write failed", 503);
  }

  // Site-content imagery is public by nature; videos/audio are private renders.
  const asset = await db.asset.create({
    data: {
      kind: sniffed.kind,
      mime: sniffed.mime,
      bytes: buf.length,
      storageKey: key,
      driver,
      isPublic: sniffed.kind === "image",
      sha256: sha256(buf),
      createdBy: "admin",
    },
  });

  return ok({ assetId: asset.id, url: `/api/files/${asset.id}`, mime: sniffed.mime, bytes: buf.length });
}

import crypto from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { bad, ok } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

const ALLOWED = new Map([
  ["image/jpeg", ".jpg"],
  ["image/png", ".png"],
  ["image/webp", ".webp"],
  // voice-clone license assets - audio evidence
  ["audio/wav", ".wav"],
  ["audio/x-wav", ".wav"],
  ["audio/wave", ".wav"],
  ["audio/mpeg", ".mp3"],
  ["audio/mp3", ".mp3"],
  ["audio/mp4", ".m4a"],
  ["audio/x-m4a", ".m4a"],
  ["audio/aac", ".aac"],
  ["audio/ogg", ".ogg"],
  ["audio/webm", ".webm"],
  // third-party written permission document
  ["application/pdf", ".pdf"],
]);

// kind -> (allowed mime set | null = all in ALLOWED, max bytes)
const KINDS = new Map<string, { mimes: Set<string> | null; maxBytes: number }>([
  ["avatar", { mimes: new Set(["image/jpeg", "image/png", "image/webp"]), maxBytes: 6 * 1024 * 1024 }],
  ["character", { mimes: new Set(["image/jpeg", "image/png", "image/webp"]), maxBytes: 6 * 1024 * 1024 }],
  ["voice-sample", { mimes: null, maxBytes: 12 * 1024 * 1024 }], // voiceprint asset
  ["voice-consent", { mimes: null, maxBytes: 8 * 1024 * 1024 }], // consent statement recording
  ["voice-written", { mimes: null, maxBytes: 8 * 1024 * 1024 }], // written permission (pdf/jpg/png)
]);

/**
 * Some browsers and tools send voice files as application/octet-stream -
 * sniff the magic bytes instead of trusting the declared type.
 */
function sniffAudio(buf: Buffer): string | null {
  if (buf.length >= 12 && buf.toString("ascii", 0, 4) === "RIFF" && buf.toString("ascii", 8, 12) === "WAVE") return "audio/wav";
  if (buf.length >= 4 && buf.toString("ascii", 0, 4) === "OggS") return "audio/ogg";
  if (buf.length >= 12 && buf.toString("ascii", 4, 8) === "ftyp") return "audio/mp4"; // m4a family
  if (buf.length >= 4 && buf[0] === 0x1a && buf[1] === 0x45 && buf[2] === 0xdf && buf[3] === 0xa3) return "audio/webm";
  if (buf.length >= 3 && buf.toString("ascii", 0, 3) === "ID3") return "audio/mpeg";
  if (buf.length >= 2 && buf[0] === 0xff && (buf[1] & 0xe0) === 0xe0) return "audio/mpeg"; // MPEG/ADTS frame sync
  return null;
}

/**
 * POST /api/studio/upload - multipart (file, kind).
 * Images: avatar | character. Voice-clone license assets: voice-sample |
 * voice-consent (audio) | voice-written (pdf/image of signed permission).
 * Stores under public/uploads/user/<id>-<rand><ext> and returns the public URL.
 * Only the extension whitelist above is accepted; uploads are served verbatim.
 */
export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);

  const form = await req.formData().catch(() => null);
  if (!form) return bad("Expected multipart form data");
  const file = form.get("file");
  const kind = String(form.get("kind") || "character");
  if (!(file instanceof File)) return bad("A file is required");

  const rule = KINDS.get(kind);
  if (!rule) return bad("kind must be avatar, character, voice-sample, voice-consent or voice-written");

  const buf = Buffer.from(await file.arrayBuffer());
  let ext = ALLOWED.get(file.type);
  if (!ext && kind.startsWith("voice-") && (file.type === "application/octet-stream" || file.type === "")) {
    const sniffed = sniffAudio(buf);
    if (sniffed) ext = ALLOWED.get(sniffed);
  }
  if (!ext) {
    if (rule.mimes && rule.mimes.has("image/jpeg")) {
      return bad("Only JPEG, PNG or WebP images are accepted");
    }
    return bad("Unsupported file type - use WAV, MP3, M4A, AAC, OGG or WebM audio, or PDF/JPEG/PNG for documents");
  }
  if (rule.mimes && !rule.mimes.has(file.type)) {
    return bad("That file type does not match this upload kind");
  }
  if (file.size > rule.maxBytes) return bad(`File is larger than ${Math.round(rule.maxBytes / (1024 * 1024))}MB`);

  const dir = path.join(process.cwd(), "public", "uploads", "user");
  await mkdir(dir, { recursive: true });
  const name = `${kind}-${user.id.slice(-6)}-${crypto.randomBytes(5).toString("hex")}${ext}`;
  await writeFile(path.join(dir, name), buf);

  return ok({ url: `/uploads/user/${name}`, kind, bytes: buf.length });
}

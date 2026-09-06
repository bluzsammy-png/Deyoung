import "server-only";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";

/**
 * W1 storage_v2 (spec §D.1): object-storage adapter with a Supabase driver and a
 * local dev driver. Bytes live OUTSIDE the database and OUTSIDE the ephemeral
 * deploy filesystem (fixes C-4); nothing is served from public/.
 *
 * Drivers are selected by STORAGE_DRIVER:
 *   - "supabase" — Supabase Storage (private bucket) via REST. Requires
 *     SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY. Survives deploys; 302 to
 *     short-lived signed URLs for delivery.
 *   - "local" (default) — ./media directory. Dev convenience ONLY: it is wiped
 *     on deploy exactly like public/uploads was. The adapter warns loudly when
 *     this driver runs with NODE_ENV=production so the limitation is never silent.
 *
 * If a driver is configured but its env vars are missing, calls fail with a
 * REQUIRES CONFIGURATION message — never a silent fallback (prompt §6/§65).
 */

export type Sniffed = { mime: string; kind: "image" | "video" | "audio"; ext: string };

/** Magic-byte MIME sniffing (spec §E.6: never trust the client's content-type). */
export function sniffMime(buf: Buffer): Sniffed | null {
  if (buf.length < 12) return null;
  const b = buf;
  const startsWith = (...bytes: number[]) => bytes.every((x, i) => b[i] === x);
  const boxAt = (off: number, s: string) =>
    b.subarray(off, off + 4).toString("latin1") === s;

  if (startsWith(0xff, 0xd8, 0xff)) return { mime: "image/jpeg", kind: "image", ext: "jpg" };
  if (startsWith(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a))
    return { mime: "image/png", kind: "image", ext: "png" };
  if (startsWith(0x47, 0x49, 0x46, 0x38)) return { mime: "image/gif", kind: "image", ext: "gif" };
  if (startsWith(0x52, 0x49, 0x46, 0x46) && boxAt(8, "WEBP"))
    return { mime: "image/webp", kind: "image", ext: "webp" };
  // ISO-BMFF family: a ftyp box at offset 4 (mp4, mov variants)
  if (boxAt(4, "ftyp")) {
    const brand = b.subarray(8, 12).toString("latin1");
    if (brand.startsWith("qt")) return { mime: "video/quicktime", kind: "video", ext: "mov" };
    return { mime: "video/mp4", kind: "video", ext: "mp4" };
  }
  if (startsWith(0x1a, 0x45, 0xdf, 0xa3)) return { mime: "video/webm", kind: "video", ext: "webm" };
  if (startsWith(0x49, 0x44, 0x33) || startsWith(0xff, 0xfb))
    return { mime: "audio/mpeg", kind: "audio", ext: "mp3" };
  if (startsWith(0x52, 0x49, 0x46, 0x46) && boxAt(8, "WAVE"))
    return { mime: "audio/wav", kind: "audio", ext: "wav" };
  if (startsWith(0x4f, 0x67, 0x67, 0x53)) return { mime: "audio/ogg", kind: "audio", ext: "ogg" };
  return null;
}

export const SIZE_CAPS = { image: 8 * 1024 * 1024, video: 200 * 1024 * 1024, audio: 50 * 1024 * 1024 };

/* ------------------------------- supabase ------------------------------- */

const BUCKET = "deyoung-media";

function supabaseEnv() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error(
      "REQUIRES CONFIGURATION: STORAGE_DRIVER=supabase needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars (Supabase dashboard → Settings → API). Set STORAGE_DRIVER=local for ephemeral dev storage."
    );
  }
  return { url: url.replace(/\/$/, ""), key };
}

async function ensureBucket(): Promise<void> {
  const { url, key } = supabaseEnv();
  const head = await fetch(`${url}/storage/v1/bucket/${BUCKET}`, {
    headers: { Authorization: `Bearer ${key}` },
  });
  if (head.ok) return;
  if (head.status === 404) {
    const created = await fetch(`${url}/storage/v1/bucket`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ name: BUCKET, public: false, fileSizeLimit: 209715200 }),
    });
    if (!created.ok && created.status !== 409 && created.status !== 400) {
      throw new Error(`Supabase bucket creation failed: HTTP ${created.status}`);
    }
    return;
  }
  throw new Error(`Supabase bucket check failed: HTTP ${head.status}`);
}

async function sbPut(key: string, data: Buffer, contentType: string): Promise<void> {
  const { url, key: k } = supabaseEnv();
  await ensureBucket();
  const res = await fetch(`${url}/storage/v1/object/${BUCKET}/${key}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${k}`,
      "Content-Type": contentType,
      "x-upsert": "true",
    },
    body: new Uint8Array(data),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Supabase upload failed: HTTP ${res.status} ${t.slice(0, 200)}`);
  }
}

async function sbSignedUrl(key: string, ttlSec: number): Promise<string> {
  const { url, key: k } = supabaseEnv();
  const res = await fetch(`${url}/storage/v1/object/sign/${BUCKET}/${key}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${k}`, "Content-Type": "application/json" },
    body: JSON.stringify({ expiresIn: ttlSec }),
  });
  if (!res.ok) {
    throw new Error(`Supabase sign failed: HTTP ${res.status}`);
  }
  const j = (await res.json()) as { signedURL?: string };
  if (!j.signedURL) throw new Error("Supabase sign returned no signedURL");
  return `${url}/storage/v1${j.signedURL.replace(/^\/storage\/v1/, "")}`;
}

async function sbDelete(key: string): Promise<void> {
  const { url, key: k } = supabaseEnv();
  const res = await fetch(`${url}/storage/v1/object/${BUCKET}/${key}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${k}` },
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`Supabase delete failed: HTTP ${res.status}`);
  }
}

/* --------------------------------- local --------------------------------- */

const LOCAL_ROOT = path.join(process.cwd(), "media");

function localPath(key: string): string {
  // keys are server-generated; still enforce containment (defense in depth)
  const p = path.join(LOCAL_ROOT, key);
  if (!p.startsWith(LOCAL_ROOT + path.sep)) throw new Error("Bad storage key");
  return p;
}

/* ------------------------------ public API ------------------------------ */

export type Driver = "supabase" | "local";

export function currentDriver(): Driver {
  const d = (process.env.STORAGE_DRIVER || "local").toLowerCase();
  if (d !== "supabase" && d !== "local") {
    throw new Error(`REQUIRES CONFIGURATION: unknown STORAGE_DRIVER "${d}" (use supabase|local)`);
  }
  return d;
}

export function storageWarning(): string | null {
  try {
    if (currentDriver() === "local" && process.env.NODE_ENV === "production") {
      return "STORAGE_DRIVER=local in production: media is wiped on every deploy (C-4). Set STORAGE_DRIVER=supabase + SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.";
    }
  } catch {
    /* invalid driver name — route handlers will surface it */
  }
  return null;
}

/** Store an object. Returns the storage key used. */
export async function putObject(
  key: string,
  data: Buffer,
  contentType: string
): Promise<{ key: string; driver: Driver }> {
  const driver = currentDriver();
  if (driver === "supabase") {
    await sbPut(key, data, contentType);
  } else {
    const p = localPath(key);
    await fs.mkdir(path.dirname(p), { recursive: true });
    await fs.writeFile(p, data);
  }
  return { key, driver };
}

/** A short-lived delivery URL. Supabase → presigned; local → null (the file route streams itself). */
export async function signedUrl(key: string, ttlSec = 600): Promise<string | null> {
  if (currentDriver() === "supabase") return sbSignedUrl(key, ttlSec);
  return null;
}

export async function getObject(key: string): Promise<Buffer | null> {
  if (currentDriver() === "supabase") {
    const { url, key: k } = supabaseEnv();
    const res = await fetch(`${url}/storage/v1/object/${BUCKET}/${key}`, {
      headers: { Authorization: `Bearer ${k}` },
    });
    if (!res.ok) return null;
    return Buffer.from(await res.arrayBuffer());
  }
  return fs.readFile(localPath(key)).catch(() => null);
}

export async function deleteObject(key: string): Promise<void> {
  if (currentDriver() === "supabase") return sbDelete(key);
  await fs.rm(localPath(key), { force: true });
}

export async function objectStat(
  key: string
): Promise<{ size: number; mtime: Date } | null> {
  if (currentDriver() === "supabase") {
    const buf = await getObject(key);
    if (!buf) return null;
    return { size: buf.length, mtime: new Date() };
  }
  const st = await fs.stat(localPath(key)).catch(() => null);
  return st ? { size: st.size, mtime: st.mtime } : null;
}

/** Deterministic object key builder. Keys never contain user-controlled path parts. */
export function buildKey(prefix: "site" | "renders" | "refs" | "audio" | "tmp", name: string): string {
  const safe = name.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 80);
  const d = new Date();
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${prefix}/${yyyy}/${mm}/${crypto.randomUUID()}-${safe}`;
}

export function sha256(buf: Buffer): string {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

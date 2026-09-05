import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

export const VOICE_LICENSE_VERSION = "v1";

/**
 * GET /api/studio/voices - the signed-in user's licensed voices.
 * `usable` = currently cleared for renders (status licensed, not revoked).
 */
export async function GET() {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const voices = await db.voiceClone.findMany({
    where: { userId: user.id },
    orderBy: { createdAt: "desc" },
    select: {
      id: true, label: true, ownerType: true, status: true,
      reviewStatus: true, licenseVersion: true, createdAt: true, revokedAt: true,
    },
  });
  return ok({
    voices: voices.map((v) => ({ ...v, usable: v.status === "licensed" })),
    licenseVersion: VOICE_LICENSE_VERSION,
  });
}

/**
 * POST /api/studio/voices - create a voice-clone license (multipart).
 *
 * Licensing model (mirrors the industry standard - ElevenLabs-style consent
 * verification, ELVIS Act / NDPA discipline):
 *   - self voice: instant. Requires a voice sample AND a recorded consent
 *     statement reading the exact scripted phrase (the license evidence).
 *   - third-party voice: requires sample + consent recording + the written
 *     permission document; stays "pending" until the site owner approves it.
 *
 * Fields: label, ownerType (self|third-party), sample (file),
 * consent (file), written (file, third-party only), acceptLicense ("yes").
 */
export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);

  const form = await req.formData().catch(() => null);
  if (!form) return bad("Expected multipart form data");

  const label = str(form.get("label"), 60).trim();
  const ownerType = String(form.get("ownerType") || "self");
  const accept = String(form.get("acceptLicense") || "");
  if (!label) return bad("Give the voice a name");
  if (ownerType !== "self" && ownerType !== "third-party") return bad("ownerType must be self or third-party");
  if (accept !== "yes") return bad("You must accept the Voice Clone License");

  const sample = form.get("sample");
  const consent = form.get("consent");
  const written = form.get("written");
  if (!(sample instanceof File) || sample.size === 0) return bad("Upload a voice sample (10+ seconds of clean speech)");
  if (!(consent instanceof File) || consent.size === 0) {
    return bad("Upload the consent recording - you reading the scripted statement");
  }
  if (ownerType === "third-party" && (!(written instanceof File) || written.size === 0)) {
    return bad("Third-party voices need the signed written permission document");
  }

  // Store through the same validated pipeline as avatars (mime whitelist + caps).
  const urls: { sample?: string; consent?: string; written?: string } = {};
  for (const [key, file] of [["voice-sample", sample], ["voice-consent", consent], ["voice-written", written]] as const) {
    if (!(file instanceof File)) continue;
    const fd = new FormData();
    fd.append("file", file, file.name || "audio");
    fd.append("kind", key);
    const res = await uploadInternal(req, fd);
    if (!res.ok) return res;
    const data = (await res.json()) as { url: string };
    urls[key.replace("voice-", "") as "sample" | "consent" | "written"] = data.url;
  }

  const status = ownerType === "self" ? "licensed" : "pending";
  const created = await db.voiceClone.create({
    data: {
      userId: user.id,
      userEmail: user.email,
      label,
      ownerType,
      sampleUrl: urls.sample!,
      consentUrl: urls.consent!,
      writtenConsentUrl: urls.written || "",
      licenseVersion: VOICE_LICENSE_VERSION,
      status,
      reviewStatus: "pending",
    },
  });

  return ok({
    voice: {
      id: created.id, label: created.label, ownerType: created.ownerType,
      status: created.status, reviewStatus: created.reviewStatus,
      licenseVersion: created.licenseVersion, createdAt: created.createdAt,
      revokedAt: null, usable: created.status === "licensed",
    },
    message:
      ownerType === "self"
        ? "Voice licensed. You can now select it in the Create tab."
        : "Received. The DeYoung owner will review the written permission before this voice activates.",
  });
}

/** DELETE /api/studio/voices?id=... - revoke a voice license. */
export async function DELETE(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const id = new URL(req.url).searchParams.get("id") || "";
  const voice = await db.voiceClone.findFirst({ where: { id, userId: user.id } });
  if (!voice) return bad("Voice not found", 404);
  await db.voiceClone.update({
    where: { id: voice.id },
    data: { status: "revoked", revokedAt: new Date() },
  });
  return ok({ revoked: true });
}

/* ---- internal helper: reuse /api/studio/upload with the caller's cookies ---- */
async function uploadInternal(req: Request, fd: FormData): Promise<Response> {
  const { POST: uploadPost } = await import("../upload/route");
  return uploadPost(new Request(new URL("/api/studio/upload", req.url), {
    method: "POST",
    headers: { cookie: req.headers.get("cookie") || "" },
    body: fd,
  }));
}

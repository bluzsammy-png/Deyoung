import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";

export const dynamic = "force-dynamic";

const CATEGORIES = ["ai-film", "style-lab", "studio", "commercial"];

/**
 * GET /api/admin/premieres — everything the Premieres tab needs in one call:
 * every premiere row (all statuses, with the owning render's prompt/email for
 * context) and the eligible delivered renders that are not on the wall yet.
 */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;

  const rows = await db.premiere.findMany({
    orderBy: [{ status: "asc" }, { postedAt: "desc" }],
    include: { request: { select: { prompt: true, email: true, seconds: true } } },
    take: 200,
  });

  const eligibleRaw = await db.videoRequest.findMany({
    where: { status: "done", resultAssetId: { not: null }, premiere: null },
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      prompt: true,
      email: true,
      seconds: true,
      resolution: true,
      resultAssetId: true,
      createdAt: true,
    },
    take: 50,
  });
  // A deduped re-render shares its asset with an already-premiered film —
  // those are not premiere-eligible (the video is on the wall once).
  const premieredAssets = await db.premiere.findMany({
    where: { assetId: { not: null } },
    select: { assetId: true },
  });
  const takenAssets = new Set(premieredAssets.map((x) => x.assetId));
  const eligible = eligibleRaw.filter((r) => !takenAssets.has(r.resultAssetId));

  return ok({
    premieres: rows.map((p) => ({
      id: p.id,
      title: p.title,
      logline: p.logline,
      category: p.category,
      durationSec: p.durationSec,
      videoUrl: p.videoUrl,
      posterUrl: p.posterUrl,
      featured: p.featured,
      status: p.status,
      source: p.source,
      requestedBy: p.requestedBy,
      postedAt: p.postedAt.toISOString(),
      videoSrc: p.assetId ? `/api/files/${p.assetId}` : p.videoUrl,
      requestId: p.requestId,
      renderPrompt: p.request?.prompt ?? "",
      renderEmail: p.request?.email ?? "",
    })),
    eligible: eligible.map((r) => ({
      id: r.id,
      prompt: r.prompt,
      email: r.email,
      seconds: r.seconds,
      resolution: r.resolution,
      resultAssetId: r.resultAssetId,
      createdAt: r.createdAt.toISOString(),
    })),
  });
}

/**
 * POST /api/admin/premieres — put a delivered render straight on the wall
 * (published immediately, asset flipped public), optionally overriding the
 * auto-filled copy. request.prompt seeds the title when none is given.
 */
export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;

  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return bad("Invalid body");
  }
  const requestId = str(body.requestId, 64);
  if (!requestId) return bad("requestId is required");

  const request = await db.videoRequest.findUnique({
    where: { id: requestId },
    include: { premiere: true },
  });
  if (!request || request.status !== "done" || !request.resultAssetId) {
    return bad("Only delivered renders can be premiered", 404);
  }
  if (request.premiere) return bad("This render already has a premiere", 409);

  const category = str(body.category, 40) || "ai-film";
  if (!CATEGORIES.includes(category)) return bad("Pick a valid category");
  const title = str(body.title, 120) || request.prompt.slice(0, 80) || "Untitled premiere";
  const logline = str(body.logline, 280);
  const posterUrl = str(body.posterUrl, 500);
  const featured = Boolean(body.featured);
  const durationSec = Math.max(0, Math.round(num(body.durationSec) || request.seconds));

  let premiere;
  try {
    premiere = await db.premiere.create({
      data: {
        requestId,
        assetId: request.resultAssetId,
        title,
        logline,
        category,
        durationSec,
        posterUrl,
        featured,
        status: "published",
        source: "admin",
        requestedBy: request.email,
      },
    });
  } catch (e) {
    // P2002 on assetId: a deduped duplicate render shares an asset that is
    // already on the wall — one video, one premiere.
    if ((e as { code?: string })?.code === "P2002") return bad("This video is already on the wall", 409);
    throw e;
  }
  // Going public: the delivered asset must be watchable by anonymous visitors.
  await db.asset.update({ where: { id: request.resultAssetId }, data: { isPublic: true } });

  return ok({ premiere: { id: premiere.id, status: premiere.status } }, 201);
}

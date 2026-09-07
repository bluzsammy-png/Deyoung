import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getUserSession } from "@/lib/users";
import { guard } from "@/lib/ratelimit";

export const dynamic = "force-dynamic";

const CATEGORIES = ["ai-film", "style-lab", "studio", "commercial"];

function videoSrc(p: { assetId: string | null; videoUrl: string }): string {
  return p.assetId ? `/api/files/${p.assetId}` : p.videoUrl;
}

/**
 * GET /api/premieres — the public Premiere Wall feed. Only published premieres
 * ever leave the database (pending user requests and rejected ones stay
 * private), featured entries pinned first, then newest.
 */
export async function GET() {
  const rows = await db.premiere.findMany({
    where: { status: "published" },
    orderBy: [{ featured: "desc" }, { postedAt: "desc" }],
    take: 60,
  });
  return ok({
    premieres: rows.map((p) => ({
      id: p.id,
      title: p.title,
      logline: p.logline,
      category: p.category,
      durationSec: p.durationSec,
      featured: p.featured,
      posterUrl: p.posterUrl,
      postedAt: p.postedAt.toISOString(),
      videoSrc: videoSrc(p),
    })),
  });
}

/**
 * POST /api/premieres — a signed-in user asks for their own delivered render to
 * premiere on the public wall. Creates a PENDING entry; nothing becomes public
 * until an admin approves it in the admin panel (the asset stays private until
 * that approval flips it).
 */
export async function POST(req: Request) {
  const limited = await guard(req, "premiere");
  if (limited) return limited;

  const s = await getUserSession();
  if (s.kind !== "ok") return bad("Sign in required", 401);

  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return bad("Invalid body");
  }
  const requestId = str(body.requestId, 64);
  const title = str(body.title, 120);
  const logline = str(body.logline, 280);
  const category = str(body.category, 40) || "ai-film";
  if (!requestId) return bad("requestId is required");
  if (!title) return bad("Give your film a title");
  if (!CATEGORIES.includes(category)) return bad("Pick a valid category");

  const request = await db.videoRequest.findUnique({
    where: { id: requestId },
    include: { premiere: true },
  });
  if (!request || request.status !== "done" || !request.resultAssetId) {
    return bad("Only delivered renders can be premiered", 404);
  }
  // Ownership: the render must belong to the signed-in user (admins may
  // premiere any delivered render directly from the admin panel).
  if (request.email !== s.user.email && s.user.role !== "admin") {
    return bad("This render is not yours", 403);
  }
  if (request.premiere) {
    return bad(
      request.premiere.status === "published"
        ? "This film is already on the wall"
        : request.premiere.status === "pending"
          ? "Your premiere request is already awaiting review"
          : "This film already had a premiere request",
      409
    );
  }

  let premiere;
  try {
    premiere = await db.premiere.create({
      data: {
        requestId,
        assetId: request.resultAssetId,
        title,
        logline,
        category,
        durationSec: request.seconds,
        status: "pending",
        source: "user",
        requestedBy: request.email,
      },
    });
  } catch (e) {
    // P2002 on assetId: the same delivered video is already on the wall or has
    // a pending request (identical re-renders share one asset by dedup).
    if ((e as { code?: string })?.code === "P2002")
      return bad("This film is already on the wall or awaiting review", 409);
    throw e;
  }
  return ok({ premiere: { id: premiere.id, status: premiere.status } }, 201);
}

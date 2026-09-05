import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export const dynamic = "force-dynamic";

/**
 * GET /api/admin/voices - every voice-clone license on file (audit view).
 * The owner can listen to the consent evidence and approve / flag / revoke.
 */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const voices = await db.voiceClone.findMany({
    orderBy: { createdAt: "desc" },
    take: 300,
  });
  return ok({ voices });
}

/**
 * PATCH /api/admin/voices - review action on a voice license.
 * body: { id, action: "approve" | "flag" | "reject" | "revoke" | "reinstate", notes? }
 *
 * approve    - third-party license cleared for use (status pending → licensed)
 * flag       - audit concern recorded; voice stays active but marked for review
 * reject     - evidence insufficient (status → rejected, unusable)
 * revoke     - license withdrawn (status → revoked, unusable)
 * reinstate  - undo a mistaken reject/revoke (status → licensed)
 */
export async function PATCH(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const body = await req.json().catch(() => ({}));
  const id = str(body.id, 40);
  const action = str(body.action, 20);
  const notes = str(body.notes, 500);
  if (!id) return bad("Voice id is required");

  const voice = await db.voiceClone.findUnique({ where: { id } });
  if (!voice) return bad("Voice not found", 404);

  const map: Record<string, { status?: string; reviewStatus?: string; revokedAt?: Date | null }> = {
    approve: { status: "licensed", reviewStatus: "approved", revokedAt: null },
    flag: { reviewStatus: "flagged" },
    reject: { status: "rejected", reviewStatus: "flagged" },
    revoke: { status: "revoked", reviewStatus: "flagged", revokedAt: new Date() },
    reinstate: { status: "licensed", reviewStatus: "approved", revokedAt: null },
  };
  const patch = map[action];
  if (!patch) return bad("action must be approve, flag, reject, revoke or reinstate");

  const updated = await db.voiceClone.update({
    where: { id },
    data: { ...patch, reviewNotes: notes || voice.reviewNotes },
  });
  return ok({ voice: updated });
}

import { db } from "@/lib/db";
import { ok } from "@/lib/api";
import { guardAdmin } from "@/lib/api";
import { str } from "@/lib/api";

/**
 * W2: admin user management — list every account with subscription + usage.
 * PATCH-style mutations live in /api/admin/users/[id].
 */
export async function GET(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const q = str(new URL(req.url).searchParams.get("q") ?? "", 100).toLowerCase();

  const users = await db.user.findMany({
    where: q
      ? { OR: [{ email: { contains: q } }, { name: { contains: q } }] }
      : undefined,
    orderBy: { createdAt: "desc" },
    take: 200,
    select: {
      id: true,
      email: true,
      name: true,
      role: true,
      status: true,
      banReason: true,
      provider: true,
      image: true,
      createdAt: true,
      lastLoginAt: true,
    },
  });

  const now = new Date();
  const subs = await db.subscription.findMany({
    where: { userId: { not: null } },
    orderBy: { createdAt: "desc" },
  });
  const subByUser = new Map<string, (typeof subs)[number]>();
  for (const s of subs) {
    if (s.userId && !subByUser.has(s.userId)) subByUser.set(s.userId, s);
  }

  const rows = await Promise.all(
    users.map(async (u) => {
      const active = subByUser.get(u.id);
      const activeOk =
        active && active.status === "active" && (!active.periodEnd || active.periodEnd > now);
      const videos = await db.videoRequest.count({
        where: { email: u.email, status: { in: ["queued", "rendering", "done"] } },
      });
      return {
        ...u,
        subscription: activeOk
          ? { planCode: active!.planCode, periodEnd: active!.periodEnd?.toISOString() ?? null }
          : null,
        videosUsed: videos,
      };
    })
  );

  return ok({ users: rows });
}

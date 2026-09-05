import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export const dynamic = "force-dynamic";

/** POST /api/support/messages-by-user - admin reads one user's thread. */
export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const userId = str(body.userId, 100);
  if (!userId) return bad("userId is required");
  const messages = await db.supportMessage.findMany({
    where: { userId },
    orderBy: { createdAt: "asc" },
    take: 200,
  });
  // customer messages count as read once the owner opens the thread
  await db.supportMessage.updateMany({ where: { userId, fromUser: true, read: false }, data: { read: true } });
  return ok({ messages });
}

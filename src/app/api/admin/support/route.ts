import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export const dynamic = "force-dynamic";

/** GET /api/admin/support - all threads, newest activity first (admin only). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;

  const messages = await db.supportMessage.findMany({ orderBy: { createdAt: "asc" }, take: 500 });
  const threads = new Map<string, { userId: string; userEmail: string; last: Date; unread: number; count: number }>();
  for (const m of messages) {
    const t = threads.get(m.userId) ?? { userId: m.userId, userEmail: m.userEmail, last: m.createdAt, unread: 0, count: 0 };
    t.last = m.createdAt;
    t.count += 1;
    if (m.fromUser && !m.read) t.unread += 1;
    threads.set(m.userId, t);
  }
  const list = [...threads.values()].sort((a, b) => b.last.getTime() - a.last.getTime());
  return ok({ threads: list });
}

/** POST /api/admin/support - owner replies into a thread { userId, body }. */
export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const userId = str(body.userId, 100);
  const text = str(body.body, 2000).trim();
  if (!userId || !text) return bad("userId and body are required");

  const user = await db.user.findUnique({ where: { id: userId } });
  if (!user) return bad("User not found", 404);

  const msg = await db.supportMessage.create({
    data: { userId, userEmail: user.email, fromUser: false, body: text, read: true },
  });
  return ok({ message: msg });
}

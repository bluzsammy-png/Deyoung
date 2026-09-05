import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

/** GET - the signed-in user's support thread (both sides, oldest last). */
export async function GET() {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const messages = await db.supportMessage.findMany({
    where: { userId: user.id },
    orderBy: { createdAt: "asc" },
    take: 200,
  });
  // user's own incoming messages count as read once fetched
  await db.supportMessage.updateMany({ where: { userId: user.id, fromUser: false, read: false }, data: { read: true } });
  return ok({ messages });
}

/** POST - user sends a message to support. */
export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  const body = await req.json().catch(() => ({}));
  const text = str(body.body, 2000).trim();
  if (!text) return bad("Type a message first");
  const msg = await db.supportMessage.create({
    data: { userId: user.id, userEmail: user.email, fromUser: true, body: text },
  });
  return ok({ message: msg });
}

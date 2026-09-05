import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getCurrentUser, hashPassword, verifyPassword } from "@/lib/auth";

export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Not signed in", 401);
  if (user.passwordHash.startsWith("google-oauth")) {
    return bad("This account signs in with Google - there is no password to change here", 400);
  }
  const body = await req.json().catch(() => ({}));
  const current = str(body.currentPassword, 200);
  const next = str(body.newPassword, 200);
  if (!verifyPassword(current, user.passwordHash)) return bad("Current password is wrong", 403);
  if (next.length < 8) return bad("New password must be at least 8 characters");
  await db.user.update({ where: { id: user.id }, data: { passwordHash: hashPassword(next) } });
  return ok({ changed: true });
}

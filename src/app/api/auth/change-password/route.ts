import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";
import { hashPassword, verifyPassword } from "@/lib/auth";

export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const body = await req.json().catch(() => ({}));
  const current = str(body.currentPassword, 200);
  const next = str(body.newPassword, 200);
  if (next.length < 8) return bad("New password must be at least 8 characters");

  const admin = await db.admin.findFirst();
  if (!admin) return bad("Admin account missing", 500);
  if (!verifyPassword(current, admin.passwordHash)) return bad("Current password is wrong", 401);

  await db.admin.update({
    where: { id: admin.id },
    data: { passwordHash: hashPassword(next) },
  });
  return ok({ changed: true });
}

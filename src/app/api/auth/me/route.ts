import { db } from "@/lib/db";
import { ok } from "@/lib/api";
import { isAdmin, isDefaultPassword } from "@/lib/auth";

export async function GET() {
  if (!(await isAdmin())) return ok({ authenticated: false });
  const admin = await db.admin.findFirst();
  return ok({
    authenticated: true,
    email: admin?.email ?? "",
    usingDefaultPassword: admin ? isDefaultPassword(admin.passwordHash) : false,
  });
}

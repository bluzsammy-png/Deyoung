import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { createSession, ensureAdmin, verifyPassword } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = str(body.email, 200).toLowerCase();
    const password = str(body.password, 200);
    if (!email || !password) return bad("Email and password are required");

    await ensureAdmin();
    const admin = await db.admin.findUnique({ where: { email } });
    if (!admin || !verifyPassword(password, admin.passwordHash)) {
      return bad("Wrong email or password", 401);
    }
    await createSession(admin);
    return ok({ authenticated: true, email: admin.email });
  } catch (e) {
    console.error("login failed", e);
    return bad("Login failed, try again", 500);
  }
}

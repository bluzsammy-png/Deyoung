import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { createUserSession, verifyPassword } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = str(body.email, 200).toLowerCase().trim();
    const password = str(body.password, 200);
    if (!email || !password) return bad("Email and password are required");

    const user = await db.user.findUnique({ where: { email } });
    if (!user || !verifyPassword(password, user.passwordHash)) {
      return bad("Wrong email or password", 401);
    }
    await createUserSession(user);
    return ok({ user: { id: user.id, email: user.email, name: user.name, avatarUrl: user.avatarUrl } });
  } catch (e) {
    console.error("user login failed", e);
    return bad("Login failed, try again", 500);
  }
}

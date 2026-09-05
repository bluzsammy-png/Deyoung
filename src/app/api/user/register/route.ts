import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { createUserSession, hashPassword } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = str(body.email, 200).toLowerCase().trim();
    const password = str(body.password, 200);
    const name = str(body.name, 120).trim();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("Enter a valid email address");
    if (password.length < 8) return bad("Password must be at least 8 characters");
    if (!name) return bad("Tell us your name");

    const exists = await db.user.findUnique({ where: { email } });
    if (exists) return bad("An account with this email already exists - sign in instead", 409);

    const user = await db.user.create({
      data: { email, passwordHash: hashPassword(password), name },
    });
    await createUserSession(user);
    return ok({ user: { id: user.id, email: user.email, name: user.name, avatarUrl: user.avatarUrl } });
  } catch (e) {
    console.error("register failed", e);
    return bad("Could not create the account, try again", 500);
  }
}

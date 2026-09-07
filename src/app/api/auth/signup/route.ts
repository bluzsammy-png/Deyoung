import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { createUser, createUserSession, ensureOwnerAdmins, findUserByEmail, isAdminEmail } from "@/lib/users";
import { guard } from "@/lib/ratelimit";

/** W2: site-user registration. Email+password (Google handled by /api/auth/google). */
export async function POST(req: Request) {
  const limited = await guard(req, "signup");
  if (limited) return limited;
  try {
    const body = await req.json().catch(() => ({}));
    const name = str(body.name, 80);
    const email = str(body.email, 200).toLowerCase();
    const password = str(body.password, 200);
    if (!email || !password) return bad("Email and password are required");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return bad("Enter a valid email address");
    if (password.length < 8) return bad("Password must be at least 8 characters");

    if (await findUserByEmail(email)) {
      return bad("An account with this email already exists — sign in instead", 409);
    }
    const user = await createUser({ email, name, password, provider: "credentials" });
    if (isAdminEmail(email)) {
      // signing up with the owner address claims the admin seat immediately
      await ensureOwnerAdmins();
      await db.user.update({ where: { id: user.id }, data: { role: "admin" } });
    }
    await db.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } });
    await createUserSession(user);
    return ok({
      user: { id: user.id, email: user.email, name: user.name, role: user.role },
      next: "/dashboard",
    }, 201);
  } catch (e) {
    console.error("signup failed", e);
    return bad("Sign up failed, try again", 500);
  }
}

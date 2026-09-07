import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { createUserSession, findUserByEmail, verifyUserPassword } from "@/lib/users";
import { guard } from "@/lib/ratelimit";

/** W2: site-user sign-in (credentials). Google uses /api/auth/google. */
export async function POST(req: Request) {
  const limited = await guard(req, "login");
  if (limited) return limited;
  try {
    const body = await req.json().catch(() => ({}));
    const email = str(body.email, 200).toLowerCase();
    const password = str(body.password, 200);
    if (!email || !password) return bad("Email and password are required");

    const user = await verifyUserPassword(email, password);
    if (!user) {
      // distinguish: account exists but is Google-only
      const existing = await findUserByEmail(email);
      if (existing && !existing.passwordHash) {
        return bad("This email is linked to Google — use \u201cContinue with Google\u201d", 400);
      }
      return bad("Wrong email or password", 401);
    }
    if (user.status !== "active") {
      const reason = user.status === "banned" ? user.banReason || "Policy violation" : "Account deactivated";
      return bad(`Account ${user.status}: ${reason}. Contact support if you think this is a mistake.`, 403);
    }
    await db.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } });
    await createUserSession(user);
    return ok({ user: { id: user.id, email: user.email, name: user.name, role: user.role } });
  } catch (e) {
    console.error("user login failed", e);
    return bad("Sign in failed, try again", 500);
  }
}

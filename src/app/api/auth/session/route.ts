import { ok } from "@/lib/api";
import { getSession } from "@/lib/auth";
import { getUserSession } from "@/lib/users";

/**
 * W2: combined session probe for the header/nav.
 * `user` = site user (dy_user cookie), `admin` = owner (dy_admin cookie).
 */
export async function GET() {
  const user = await getUserSession();
  const adminPayload = await getSession();
  return ok({
    user:
      user.kind === "ok"
        ? {
            id: user.user.id,
            email: user.user.email,
            name: user.user.name,
            image: user.user.image,
            role: user.user.role,
          }
        : null,
    userBlocked: user.kind === "blocked" ? { status: user.status, reason: user.reason } : null,
    admin:
      adminPayload && adminPayload.role !== "user"
        ? { email: adminPayload.email }
        : null,
  });
}

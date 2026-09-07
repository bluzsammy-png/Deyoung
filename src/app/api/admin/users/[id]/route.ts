import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";
import { isAdminEmail, ensureOwnerAdmins } from "@/lib/users";

type Action = "ban" | "activate" | "deactivate" | "make-admin" | "remove-admin";

/**
 * W2: full admin control over one user account.
 * ban (with reason, blocks every guarded route) · activate (un-ban) ·
 * deactivate (soft lock) · make-admin / remove-admin (role flip).
 * Owner-allowlisted emails can never be demoted or banned — fail closed.
 */
export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const action = str(body.action, 20) as Action;
  const reason = str(body.reason, 200);

  const user = await db.user.findUnique({ where: { id } });
  if (!user) return bad("User not found", 404);

  const isOwnerSeat = isAdminEmail(user.email);
  if (isOwnerSeat && action !== "activate") {
    return bad("This address is the owner seat (ADMIN_EMAILS) — it cannot be banned, deactivated or demoted.", 403);
  }

  switch (action) {
    case "ban":
      if (!reason) return bad("A ban reason is required");
      await db.user.update({ where: { id }, data: { status: "banned", banReason: reason } });
      break;
    case "activate":
      await db.user.update({ where: { id }, data: { status: "active", banReason: "" } });
      break;
    case "deactivate":
      await db.user.update({
        where: { id },
        data: { status: "deactivated", banReason: reason || "Deactivated by the owner" },
      });
      break;
    case "make-admin":
      await db.user.update({ where: { id }, data: { role: "admin" } });
      break;
    case "remove-admin":
      await db.user.update({ where: { id }, data: { role: "user" } });
      break;
    default:
      return bad("Unknown action");
  }

  if (action === "make-admin" && isOwnerSeat) await ensureOwnerAdmins();
  const updated = await db.user.findUnique({
    where: { id },
    select: { id: true, email: true, role: true, status: true, banReason: true },
  });
  return ok({ user: updated });
}

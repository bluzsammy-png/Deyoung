import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";

/** Admin: list every subscription. Authed users: create a pending subscription (checkout step 2). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const subs = await db.subscription.findMany({ orderBy: { createdAt: "desc" } });
  return ok({ subscriptions: subs });
}

/**
 * Subscriptions are never standalone: creating one requires a signed-in
 * DeYoung account, so the plan is always attached to a real user.
 */
export async function POST(req: Request) {
  const user = await getCurrentUser();
  if (!user) return bad("Sign up or sign in first - every plan belongs to an account", 401);

  const body = await req.json().catch(() => ({}));
  const planCode = str(body.planCode, 40);

  const plan = await db.plan.findUnique({ where: { code: planCode } });
  if (!plan || !plan.active) return bad("Pick a valid plan");

  // If this account already has an active subscription, don't double-bill -
  // point the user at their studio instead.
  const existing = await db.subscription.findFirst({
    where: { userId: user.id, status: "active", periodEnd: { gt: new Date() } },
  });
  if (existing) {
    return bad("This account already has an active plan - manage it from your studio", 409);
  }

  const sub = await db.subscription.create({
    data: {
      name: user.name || str(body.name, 120) || "DeYoung subscriber",
      email: user.email,
      userId: user.id,
      phone: str(body.phone, 60),
      planCode: plan.code,
      pricePaid: plan.priceMonthly,
      currency: plan.currency,
      provider: str(body.provider, 30) || "manual",
      notes: str(body.notes, 2000),
    },
  });

  return ok({ subscription: sub }, 201);
}

import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";
import { guard } from "@/lib/ratelimit";

/** Admin: list every subscription. Public: create a pending subscription (checkout step 1). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const subs = await db.subscription.findMany({ orderBy: { createdAt: "desc" } });
  return ok({ subscriptions: subs });
}

export async function POST(req: Request) {
  const limited = await guard(req, "submit");
  if (limited) return limited;
  const body = await req.json().catch(() => ({}));
  const name = str(body.name, 120);
  const email = str(body.email, 200).toLowerCase();
  const phone = str(body.phone, 60);
  const planCode = str(body.planCode, 40);

  if (!name || !email) return bad("Name and email are required");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("That email does not look right");

  const plan = await db.plan.findUnique({ where: { code: planCode } });
  if (!plan || !plan.active) return bad("Pick a valid plan");

  const sub = await db.subscription.create({
    data: {
      name,
      email,
      phone,
      planCode: plan.code,
      pricePaid: plan.priceMonthly,
      currency: plan.currency,
      provider: str(body.provider, 30) || "manual",
      notes: str(body.notes, 2000),
    },
  });

  return ok({ subscription: sub }, 201);
}

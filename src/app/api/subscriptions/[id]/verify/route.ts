import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getSettings } from "@/lib/settings";
import { getCurrentUser } from "@/lib/auth";

type Ctx = { params: Promise<{ id: string }> };

/**
 * Public verification endpoint for subscriptions: after hosted checkout returns a
 * reference, the server confirms it with the provider's SECRET key before activating
 * the subscription. Without a configured secret, the owner activates manually.
 */
export async function POST(req: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const reference = str(body.reference, 200);
  if (!reference) return bad("Payment reference is required");

  const sub = await db.subscription.findUnique({ where: { id } });
  if (!sub) return bad("Subscription not found", 404);

  const s = await getSettings();
  if (!s.paymentSecretKey) {
    return ok({ verified: false, reason: "manual-activation", subscription: sub });
  }

  try {
    let success = false;

    if (s.paymentProvider === "paystack") {
      const res = await fetch(
        `https://api.paystack.co/transaction/verify/${encodeURIComponent(reference)}`,
        { headers: { Authorization: `Bearer ${s.paymentSecretKey}` } }
      );
      const json = await res.json();
      success =
        !!json?.data &&
        json.data.status === "success" &&
        Number(json.data.amount) === Math.round(sub.pricePaid * 100);
    } else if (s.paymentProvider === "flutterwave") {
      const res = await fetch(
        `https://api.flutterwave.com/v3/transactions/verify_by_reference?reference=${encodeURIComponent(reference)}`,
        { headers: { Authorization: `Bearer ${s.paymentSecretKey}` } }
      );
      const json = await res.json();
      success =
        !!json?.data &&
        json.data.status === "successful" &&
        Number(json.data.amount) === Number(sub.pricePaid);
    } else {
      return ok({ verified: false, reason: "provider-does-not-need-verification", subscription: sub });
    }

    if (!success) return ok({ verified: false, reason: "not-successful", subscription: sub });

    const periodEnd = new Date();
    periodEnd.setMonth(periodEnd.getMonth() + 1);
    // Belt & braces: make sure the activating account owns this subscription.
    const me = await getCurrentUser();
    const updated = await db.subscription.update({
      where: { id },
      data: {
        status: "active",
        periodStart: sub.periodStart ?? new Date(),
        periodEnd,
        paymentRef: reference,
        ...(me && !sub.userId ? { userId: me.id } : {}),
      },
    });
    return ok({ verified: true, subscription: updated });
  } catch (e) {
    console.error("subscription verification error", e);
    return bad("Could not verify payment right now", 502);
  }
}

import { createHmac, timingSafeEqual } from "node:crypto";
import { db } from "@/lib/db";
import { getSettings } from "@/lib/settings";

export const dynamic = "force-dynamic";

/**
 * POST /api/payments/webhook/paystack - server-to-server payment confirmation.
 *
 * Paystack signs every webhook payload with HMAC-SHA512 using your SECRET key.
 * We verify the signature against the RAW body (never the parsed object), then
 * activate the matching subscription or booking. Idempotent: a charge we have
 * already processed returns 200 so Paystack stops retrying.
 *
 * Set the webhook URL in the Paystack dashboard to:
 *   https://<your-domain>/api/payments/webhook/paystack
 */
export async function POST(req: Request) {
  const raw = await req.text();
  const signature = req.headers.get("x-paystack-signature") || "";

  const s = await getSettings();
  if (s.paymentProvider !== "paystack" || !s.paymentSecretKey) {
    // Not configured - accept-and-ignore so Paystack doesn't hammer a 500.
    return Response.json({ received: true, note: "paystack-not-configured" });
  }

  const expected = createHmac("sha512", s.paymentSecretKey).update(raw).digest("hex");
  const a = Buffer.from(signature);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    return Response.json({ error: "invalid signature" }, { status: 401 });
  }

  let event: { event?: string; data?: Record<string, unknown> };
  try {
    event = JSON.parse(raw);
  } catch {
    return Response.json({ error: "bad payload" }, { status: 400 });
  }

  if (event.event !== "charge.success") {
    return Response.json({ received: true });
  }

  const data = event.data || {};
  const reference = String(data.reference || "");
  const amountKobo = Number(data.amount || 0);
  if (!reference) return Response.json({ received: true });

  // ---- subscription payment (reference = subscription.id) ----
  const sub = await db.subscription.findUnique({ where: { id: reference } }).catch(() => null);
  if (sub && sub.status !== "active") {
    if (amountKobo > 0 && amountKobo !== Math.round(sub.pricePaid * 100)) {
      return Response.json({ received: true, note: "amount-mismatch" });
    }
    const periodEnd = new Date();
    periodEnd.setMonth(periodEnd.getMonth() + 1);
    await db.subscription.update({
      where: { id: sub.id },
      data: {
        status: "active",
        periodStart: sub.periodStart ?? new Date(),
        periodEnd,
        paymentRef: String(data.id || reference),
        provider: "paystack",
      },
    });
    return Response.json({ received: true, activated: "subscription" });
  }
  if (sub) return Response.json({ received: true, note: "already-active" });

  // ---- booking payment (reference = booking.id) ----
  const booking = await db.booking.findUnique({ where: { id: reference } }).catch(() => null);
  if (booking && booking.status === "pending") {
    await db.booking.update({
      where: { id: booking.id },
      data: {
        status: "paid",
        paymentRef: String(data.id || reference),
        provider: "paystack",
      },
    });
    return Response.json({ received: true, activated: "booking" });
  }

  return Response.json({ received: true });
}

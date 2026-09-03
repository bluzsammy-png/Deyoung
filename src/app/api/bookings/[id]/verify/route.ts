import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getSettings } from "@/lib/settings";

type Ctx = { params: Promise<{ id: string }> };

/**
 * Public verification endpoint: after the hosted checkout returns a reference,
 * the server confirms it with the provider's SECRET key before marking the
 * booking paid. Without a configured secret, the owner confirms payments
 * manually from the dashboard instead.
 */
export async function POST(req: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  const reference = str(body.reference, 200);
  if (!reference) return bad("Payment reference is required");

  const booking = await db.booking.findUnique({ where: { id } });
  if (!booking) return bad("Booking not found", 404);

  const s = await getSettings();
  if (!s.paymentSecretKey) {
    return ok({ verified: false, reason: "manual-confirmation", booking });
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
        Number(json.data.amount) === Math.round(booking.amount * 100);
    } else if (s.paymentProvider === "flutterwave") {
      const res = await fetch(
        `https://api.flutterwave.com/v3/transactions/verify_by_reference?reference=${encodeURIComponent(reference)}`,
        { headers: { Authorization: `Bearer ${s.paymentSecretKey}` } }
      );
      const json = await res.json();
      success =
        !!json?.data &&
        json.data.status === "successful" &&
        Number(json.data.amount) === Number(booking.amount);
    } else {
      return ok({ verified: false, reason: "provider-does-not-need-verification", booking });
    }

    if (!success) return ok({ verified: false, reason: "not-successful", booking });

    const updated = await db.booking.update({
      where: { id },
      data: { status: "paid", paymentRef: reference },
    });
    return ok({ verified: true, booking: updated });
  } catch (e) {
    console.error("payment verification error", e);
    return bad("Could not verify payment right now", 502);
  }
}

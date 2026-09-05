import { db } from "@/lib/db";
import { bad, guardAdmin, ok, num, str } from "@/lib/api";
import { getSettings } from "@/lib/settings";
import { sendOwnerEmail } from "@/lib/agentmail";

/** Public: create a booking (used by the checkout flow). */
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const name = str(body.name, 120);
  const email = str(body.email, 200);
  const phone = str(body.phone, 40);
  const serviceTitle = str(body.serviceTitle, 200);
  const notes = str(body.notes, 2000);
  const amount = num(body.amount);
  if (!name || !email || !serviceTitle) return bad("Name, email and service are required");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("Please enter a valid email");

  const s = await getSettings();
  const booking = await db.booking.create({
    data: {
      name,
      email,
      phone,
      serviceTitle,
      amount,
      currency: s.currency,
      notes,
      provider: s.paymentProvider,
      status: "pending",
    },
  });

  // Notify the owner's AgentMail inbox (non-fatal: booking is already saved).
  void sendOwnerEmail({
    subject: `New booking - ${serviceTitle} (${s.currency} ${amount ?? 0})`,
    replyTo: email,
    text: [
      `You have a new booking from the website.`,
      ``,
      `Customer:  ${name}`,
      `Email:     ${email}`,
      `Phone:     ${phone || "-"}`,
      `Service:   ${serviceTitle}`,
      `Amount:    ${s.currency} ${amount ?? 0}`,
      `Payment:   ${s.paymentProvider}`,
      `Notes:     ${notes || "-"}`,
      ``,
      `Open the admin panel to confirm, or reply to this email to reach ${name}.`,
    ].join("\n"),
  }).catch(() => {});

  return ok({ booking });
}

/** Admin: list all bookings (= your customers/users). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const bookings = await db.booking.findMany({ orderBy: { createdAt: "desc" } });
  return ok({ bookings });
}

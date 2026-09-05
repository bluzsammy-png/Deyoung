"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, money, type Booking } from "@/lib/types";
import { go } from "./hash";
import { SectionHead } from "./sections";

export function ThankYouView({
  bookingId,
  paid,
  siteName,
}: {
  bookingId?: string;
  paid?: boolean;
  siteName: string;
}) {
  const [booking, setBooking] = useState<Booking | null>(null);

  useEffect(() => {
    // Light fetch of the booking for a personalised confirmation.
    if (!bookingId) return;
    api<{ bookings: Booking[] }>("/api/bookings")
      .then((r) => setBooking(r.bookings.find((b) => b.id === bookingId) ?? null))
      .catch(() => setBooking(null));
  }, [bookingId]);

  return (
    <section className="py-16 md:py-24 bg-white min-h-[70vh]">
      <div className="mx-auto max-w-2xl px-4 text-center">
        <div className="mx-auto h-20 w-20 bg-primary flex items-center justify-center" aria-hidden>
          <CheckCircle2 className="h-10 w-10 text-white" />
        </div>
        <h1 className="mt-6 text-4xl font-black uppercase tracking-tight">
          {paid ? "Payment Confirmed" : "Booking Received"}
        </h1>
        <p className="mt-4 text-neutral-600 leading-relaxed">
          {paid
            ? `Your payment went through and your booking is locked in. ${siteName} will reach out with the next steps.`
            : `Your booking is in. Complete payment if you haven't yet, and ${siteName} will confirm your slot within 24 hours.`}
        </p>

        {booking ? (
          <div className="mt-8 border-2 border-[var(--brand-black)] p-5 text-left">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <p className="text-xs uppercase tracking-widest font-bold text-muted-foreground">Reference</p>
                <p className="font-mono font-black">{booking.id.slice(0, 10).toUpperCase()}</p>
              </div>
              <span
                className={`text-xs font-black uppercase px-3 py-1.5 ${
                  booking.status === "paid" || booking.status === "confirmed"
                    ? "bg-primary text-white"
                    : "bg-neutral-200 text-neutral-700"
                }`}
              >
                {booking.status}
              </span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-muted-foreground">Service</dt>
                <dd className="font-bold">{booking.serviceTitle}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Amount</dt>
                <dd className="font-bold">{money(booking.amount, booking.currency)}</dd>
              </div>
            </dl>
          </div>
        ) : null}

        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={() => go("#")} className="h-12 px-6 bg-[var(--brand-black)] hover:bg-primary text-white font-bold">
            <Home className="h-4 w-4" aria-hidden /> Back to Home
          </Button>
        </div>

        <p className="mt-8 inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4 text-primary" aria-hidden /> Expect a reply within 24 hours - usually much faster.
        </p>
      </div>
    </section>
  );
}

export function PrivacyView({ siteName, contactEmail }: { siteName: string; contactEmail: string }) {
  return (
    <section className="py-12 md:py-20 bg-white min-h-[70vh]">
      <div className="mx-auto max-w-3xl px-4">
        <SectionHead kicker="Legal" title="Privacy Policy" dark={false} />
        <div className="mt-8 space-y-6 text-sm md:text-base leading-relaxed text-neutral-700">
          <p>
            <strong>{siteName}</strong> (&quot;we&quot;, &quot;the site&quot;) respects your privacy. This
            policy explains, in plain language, what information the site collects and how it is used.
            By using this site you agree to the practices described here.
          </p>
          <div>
            <h3 className="font-black uppercase text-base">What we collect</h3>
            <ul className="mt-2 list-disc pl-5 space-y-1.5">
              <li><strong>Bookings:</strong> your name, email, phone number and any notes you provide when booking a service.</li>
              <li><strong>Messages:</strong> the name, email and message content you send through the contact form.</li>
              <li><strong>Payments:</strong> handled entirely by the payment provider (e.g. Paystack, Flutterwave, PayPal or Stripe). Your card details never touch this site - we only store your booking reference and payment status.</li>
            </ul>
          </div>
          <div>
            <h3 className="font-black uppercase text-base">How it is used</h3>
            <p className="mt-2">
              Your information is used only to deliver the service you booked, contact you about your
              booking, and keep records of orders. It is never sold or shared with advertisers. Payment
              references are shared with the payment provider strictly to verify transactions.
            </p>
          </div>
          <div>
            <h3 className="font-black uppercase text-base">Who can see your data</h3>
            <p className="mt-2">
              Only the site owner, via a private, password-protected admin panel. All admin sessions
              are authenticated and expire automatically. Visitors of the site cannot see your booking
              or message details.
            </p>
          </div>
          <div>
            <h3 className="font-black uppercase text-base">Your rights</h3>
            <p className="mt-2">
              You can ask at any time to see, correct or delete the personal information you left on
              this site. Just email{" "}
              <a href={`mailto:${contactEmail}`} className="font-bold text-primary underline underline-offset-4">
                {contactEmail}
              </a>{" "}
              and it will be handled promptly.
            </p>
          </div>
          <div>
            <h3 className="font-black uppercase text-base">Changes</h3>
            <p className="mt-2">
              If this policy changes, the updated version will be posted on this page. Continued use
              of the site after changes means you accept the updated policy.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

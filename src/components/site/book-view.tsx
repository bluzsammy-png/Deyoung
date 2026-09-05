"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { BadgeCheck, CalendarArrowDown, Clapperboard, CreditCard, Landmark, Loader2, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, money, type Booking, type Plan, type PublicSettings, type Service, type Subscription } from "@/lib/types";
import { go } from "./hash";
import { SectionHead } from "./sections";

type PayWindow = Window & {
  PaystackPop?: {
    setup: (o: {
      key: string;
      email: string;
      amount: number;
      currency: string;
      ref: string;
      callback: (r: { reference: string }) => void;
      onClose: () => void;
    }) => { openIframe: () => void };
  };
  FlutterwaveCheckout?: (o: Record<string, unknown>) => void;
  paypal?: {
    Buttons: (o: Record<string, unknown>) => { render: (sel: string | HTMLElement) => Promise<void> };
  };
};

function loadScript(src: string, id: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.getElementById(id);
    if (existing) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.id = id;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load payment script"));
    document.head.appendChild(s);
  });
}

const PROVIDER_LABEL: Record<string, string> = {
  manual: "Bank transfer / Mobile money",
  paystack: "Card, bank transfer & mobile money (Paystack)",
  flutterwave: "Card, bank transfer & mobile money (Flutterwave)",
  paypal: "PayPal / Card",
  stripe: "Card (Stripe)",
};

/** One checkout view for both flows: service bookings and plan subscriptions. */
type Order = {
  id: string;
  email: string;
  name: string;
  phone: string;
  amount: number;
  currency: string;
  title: string;
  status: string;
};

export function BookView({
  settings,
  services,
  plans = [],
  mode = "booking",
  preselect,
  preselectPlan,
}: {
  settings: PublicSettings | null;
  services: Service[];
  plans?: Plan[];
  mode?: "booking" | "subscription";
  preselect?: string;
  preselectPlan?: string;
}) {
  const s = settings;
  const [form, setForm] = useState({ name: "", email: "", phone: "", notes: "" });
  const [serviceId, setServiceId] = useState(preselect || "");
  const [planCode, setPlanCode] = useState(preselectPlan || "");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<"form" | "pay">("form");
  const [booking, setBooking] = useState<Booking | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const paypalRef = useRef<HTMLDivElement>(null);

  const service = useMemo(
    () => services.find((x) => x.id === serviceId) || null,
    [services, serviceId]
  );
  const plan = useMemo(
    () => plans.find((p) => p.code === planCode) || null,
    [plans, planCode]
  );

  useEffect(() => {
    if (preselect) setServiceId(preselect);
  }, [preselect]);
  useEffect(() => {
    if (preselectPlan) setPlanCode(preselectPlan);
  }, [preselectPlan]);

  /** Unified view over whichever entity is being paid right now. */
  const order: Order | null = useMemo(() => {
    if (mode === "subscription") {
      if (!sub) return null;
      return {
        id: sub.id,
        email: sub.email,
        name: sub.name,
        phone: sub.phone,
        amount: sub.pricePaid,
        currency: sub.currency,
        title: `${plan?.name || sub.planCode} plan - 1 month`,
        status: sub.status,
      };
    }
    if (!booking) return null;
    return {
      id: booking.id,
      email: booking.email,
      name: booking.name,
      phone: booking.phone,
      amount: booking.amount,
      currency: booking.currency,
      title: booking.serviceTitle,
      status: booking.status,
    };
  }, [mode, sub, booking, plan]);

  async function createBooking(e: React.FormEvent) {
    e.preventDefault();
    if (!service) return toast.error("Pick a service first");
    setBusy(true);
    try {
      const res = await api<{ booking: Booking }>("/api/bookings", {
        method: "POST",
        body: JSON.stringify({ ...form, serviceTitle: service.title, amount: service.price }),
      });
      setBooking(res.booking);
      setStage("pay");
      if (s?.paymentProvider === "paypal") initPaypal(res.booking);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create booking");
    } finally {
      setBusy(false);
    }
  }

  async function createSubscription(e: React.FormEvent) {
    e.preventDefault();
    if (!plan) return toast.error("Pick a plan first");
    setBusy(true);
    try {
      const res = await api<{ subscription: Subscription }>("/api/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          planCode: plan.code,
          provider: s?.paymentProvider || "manual",
        }),
      });
      setSub(res.subscription);
      setStage("pay");
      if (s?.paymentProvider === "paypal") initPaypalSub(res.subscription);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create subscription");
    } finally {
      setBusy(false);
    }
  }

  async function confirmPaid(reference: string) {
    if (mode === "subscription") {
      if (!sub) return;
      try {
        const res = await api<{ verified: boolean; subscription: Subscription }>(
          `/api/subscriptions/${sub.id}/verify`,
          { method: "POST", body: JSON.stringify({ reference }) }
        );
        if (res.verified) {
          toast.success("Subscription active - time to make some videos!");
          go("#request");
        } else {
          toast.message("Payment received - the owner will activate your subscription shortly.");
          setStage("form");
        }
      } catch {
        toast.message("Subscription saved. Activation pending.");
      }
      return;
    }
    if (!booking) return;
    try {
      const res = await api<{ verified: boolean; booking: Booking }>(
        `/api/bookings/${booking.id}/verify`,
        { method: "POST", body: JSON.stringify({ reference }) }
      );
      if (res.verified) {
        toast.success("Payment confirmed!");
        go(`#thanks?b=${booking.id}&paid=1`);
      } else {
        toast.message("Payment received - the owner will confirm it shortly.");
        go(`#thanks?b=${booking.id}`);
      }
    } catch {
      toast.message("Booking saved. Payment confirmation pending.");
      go(`#thanks?b=${booking.id}`);
    }
  }

  /* ---------- provider starters ---------- */

  async function startPaystack() {
    if (!order || !s?.paymentPublicKey) return toast.error("Payment is not set up yet - choose another option");
    try {
      await loadScript("https://js.paystack.co/v1/inline.js", "paystack-inline");
      const w = window as PayWindow;
      if (!w.PaystackPop) throw new Error("Paystack unavailable");
      const handler = w.PaystackPop.setup({
        key: s.paymentPublicKey,
        email: order.email,
        amount: Math.round(order.amount * 100),
        currency: order.currency,
        ref: order.id,
        callback: (r) => confirmPaid(r.reference),
        onClose: () => toast.message("Payment window closed - your order is still saved."),
      });
      handler.openIframe();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start payment");
    }
  }

  function startFlutterwave() {
    if (!order || !s?.paymentPublicKey) return toast.error("Payment is not set up yet - choose another option");
    const w = window as PayWindow;
    w.FlutterwaveCheckout?.({
      public_key: s.paymentPublicKey,
      tx_ref: order.id,
      amount: order.amount,
      currency: order.currency,
      payment_options: "card,banktransfer,ussd,mobilemoneyghana,mobilemoneynigeria",
      customer: { email: order.email, phone_number: order.phone, name: order.name },
      customizations: { description: order.title.slice(0, 120) },
      callback: (data: { transaction_id?: string; tx_ref?: string }) => {
        confirmPaid(data.tx_ref || order.id);
      },
      onclose: () => toast.message("Payment window closed - your order is still saved."),
    });
  }

  function startStripe() {
    if (!s?.paymentLinkUrl) return toast.error("Payment link is not set up yet");
    window.location.href = s.paymentLinkUrl;
  }

  function initPaypal(b: Booking) {
    if (!s?.paymentPublicKey) return;
    loadScript(
      `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(s.paymentPublicKey)}&currency=${b.currency}&intent=capture`,
      "paypal-sdk"
    )
      .then(() => {
        const w = window as PayWindow;
        if (!w.paypal || !paypalRef.current) return;
        w.paypal
          .Buttons({
            style: { color: "black", label: "pay" },
            createOrder: (_data: unknown, actions: { order: { create: (o: Record<string, unknown>) => Promise<string> } }) =>
              actions.order.create({
                purchase_units: [
                  {
                    amount: { value: b.amount.toFixed(2), currency_code: b.currency },
                    description: `Booking: ${b.serviceTitle}`.slice(0, 127),
                  },
                ],
              }),
            onApprove: async (data: unknown, actions: { order: { capture: () => Promise<{ id: string }> } }) => {
              const details = await actions.order.capture();
              await confirmPaid(details.id || b.id);
            },
            onError: () => toast.error("PayPal error - try again or pick another method"),
          })
          .render(paypalRef.current)
          .catch(() => toast.error("Could not render PayPal buttons"));
      })
      .catch(() => toast.error("Could not load PayPal"));
  }

  function initPaypalSub(sub2: Subscription) {
    if (!s?.paymentPublicKey) return;
    loadScript(
      `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(s.paymentPublicKey)}&currency=${sub2.currency}&intent=capture`,
      "paypal-sdk"
    )
      .then(() => {
        const w = window as PayWindow;
        if (!w.paypal || !paypalRef.current) return;
        w.paypal
          .Buttons({
            style: { color: "black", label: "pay" },
            createOrder: (_data: unknown, actions: { order: { create: (o: Record<string, unknown>) => Promise<string> } }) =>
              actions.order.create({
                purchase_units: [
                  {
                    amount: { value: sub2.pricePaid.toFixed(2), currency_code: sub2.currency },
                    description: `${plan?.name || sub2.planCode} plan subscription`.slice(0, 127),
                  },
                ],
              }),
            onApprove: async (data: unknown, actions: { order: { capture: () => Promise<{ id: string }> } }) => {
              const details = await actions.order.capture();
              await confirmPaid(details.id || sub2.id);
            },
            onError: () => toast.error("PayPal error - try again or pick another method"),
          })
          .render(paypalRef.current)
          .catch(() => toast.error("Could not render PayPal buttons"));
      })
      .catch(() => toast.error("Could not load PayPal"));
  }

  const provider = s?.paymentProvider || "manual";
  const needsKey = ["paystack", "flutterwave", "paypal"].includes(provider);
  const providerReady = !needsKey || (provider === "stripe" ? !!s?.paymentLinkUrl : !!s?.paymentPublicKey);

  /* ---------- render ---------- */

  return (
    <section className="py-12 md:py-20 bg-white min-h-[70vh]">
      <div className="mx-auto max-w-3xl px-4">
        <SectionHead
          kicker={mode === "subscription" ? "AI Video Subscription" : "Booking"}
          title={stage === "form" ? (mode === "subscription" ? "Pick Your Plan" : "Book Your Service") : "Complete Payment"}
          dark={false}
        />

        {stage === "form" ? (
          mode === "subscription" ? (
            <form onSubmit={createSubscription} className="mt-10 space-y-5" aria-label="Subscription form">
              <div className="space-y-2">
                <Label htmlFor="s-plan">Plan</Label>
                <select
                  id="s-plan"
                  required
                  value={planCode}
                  onChange={(e) => setPlanCode(e.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">Choose a plan…</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.code}>
                      {p.name} - {money(p.priceMonthly, p.currency || s?.currency || "USD")}/mo - {p.maxVideosMonth} videos, up to {p.maxSecondsVideo}s
                    </option>
                  ))}
                </select>
              </div>
              {plan && (
                <p className="text-sm text-neutral-600 border-l-4 border-primary pl-3">
                  {plan.blurb} Renders at {plan.maxResolution}
                  {plan.watermark ? " with the DeYoung watermark" : " with no watermark"}.
                </p>
              )}
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="s-name">Your name</Label>
                  <Input id="s-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-email">Email</Label>
                  <Input id="s-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
                </div>
              </div>
              <div className="space-y-2 max-w-sm">
                <Label htmlFor="s-phone">Phone / WhatsApp (optional)</Label>
                <Input id="s-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+1 555 000 0000" />
              </div>

              {plan && (
                <div className="border-2 border-[var(--brand-black)] p-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest font-bold text-muted-foreground">You are subscribing to</p>
                    <p className="font-black text-lg">{plan.name} - monthly</p>
                    <p className="text-xs text-muted-foreground">
                      {plan.maxVideosMonth} videos/month · up to {plan.maxSecondsVideo}s · {plan.maxResolution}
                    </p>
                  </div>
                  <p className="text-3xl font-black text-primary">{money(plan.priceMonthly, plan.currency || s?.currency || "USD")}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={busy}
                className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Clapperboard className="h-4 w-4" aria-hidden />}
                {busy ? "Creating subscription…" : "Continue to Payment"}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Billed monthly. Cancel anytime - payment options include bank transfer, mobile money and international cards.
              </p>
            </form>
          ) : (
            <form onSubmit={createBooking} className="mt-10 space-y-5" aria-label="Booking form">
              <div className="space-y-2">
                <Label htmlFor="b-service">Service</Label>
                <select
                  id="b-service"
                  required
                  value={serviceId}
                  onChange={(e) => setServiceId(e.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">Choose a service…</option>
                  {services.map((sv) => (
                    <option key={sv.id} value={sv.id}>
                      {sv.title} - {money(sv.price, s?.currency || "USD")}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="b-name">Your name</Label>
                  <Input id="b-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="b-email">Email</Label>
                  <Input id="b-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="b-phone">Phone / WhatsApp (optional)</Label>
                  <Input id="b-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+1 555 000 0000" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="b-notes">Notes (optional)</Label>
                  <Input id="b-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Date, location, ideas…" />
                </div>
              </div>

              {service && (
                <div className="border-2 border-[var(--brand-black)] p-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest font-bold text-muted-foreground">You are booking</p>
                    <p className="font-black text-lg">{service.title}</p>
                    {service.duration ? <p className="text-xs text-muted-foreground">{service.duration}</p> : null}
                  </div>
                  <p className="text-3xl font-black text-primary">{money(service.price, s?.currency || "USD")}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={busy}
                className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <CalendarArrowDown className="h-4 w-4" aria-hidden />}
                {busy ? "Creating booking…" : "Continue to Payment"}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Payment options at the next step include bank transfer, mobile money and international cards.
              </p>
            </form>
          )
        ) : order ? (
          <div className="mt-10 space-y-6">
            <div className="border-2 border-primary p-5">
              <p className="text-xs uppercase tracking-widest font-bold text-muted-foreground">
                {mode === "subscription" ? "Subscription reference" : "Booking reference"}
              </p>
              <p className="font-mono font-black text-lg">{order.id.slice(0, 10).toUpperCase()}</p>
              <p className="mt-2 text-sm text-neutral-600">
                {order.title} for <strong>{order.name}</strong> -{" "}
                <span className="font-black text-primary">{money(order.amount, order.currency)}</span>
              </p>
            </div>

            {provider === "manual" && (
              <div className="space-y-4">
                <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                  <Landmark className="h-5 w-5 text-primary" aria-hidden /> Pay by bank / mobile money
                </h3>
                {s?.bankDetails ? (
                  <pre className="bg-[#F7F7F7] border-2 border-neutral-200 p-4 text-sm whitespace-pre-wrap font-sans">{s.bankDetails}</pre>
                ) : null}
                <p className="text-sm text-neutral-600 leading-relaxed">{s?.paymentInstructions}</p>
                <div className="relative aspect-[4/1] w-full overflow-hidden border" aria-hidden>
                  <Image src="/img/pay-methods.png" alt="" fill sizes="100vw" className="object-cover" />
                </div>
                <Button
                  onClick={() =>
                    mode === "subscription"
                      ? (toast.message("Saved! The owner will activate your subscription as soon as the payment lands."),
                        setStage("form"))
                      : go(`#thanks?b=${order.id}`)
                  }
                  className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold"
                >
                  I&apos;ve Sent the Payment <BadgeCheck className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            )}

            {provider === "paystack" && (
              <div className="space-y-4">
                <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" aria-hidden /> Card, bank & mobile money
                </h3>
                {providerReady ? (
                  <Button onClick={startPaystack} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold">
                    Pay {money(order.amount, order.currency)} Securely
                  </Button>
                ) : (
                  <Notice text="Card payment is being connected. Use a bank transfer for now - contact the owner for details." />
                )}
              </div>
            )}

            {provider === "flutterwave" && (
              <div className="space-y-4">
                <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" aria-hidden /> Card, bank & mobile money
                </h3>
                {providerReady ? (
                  <Button onClick={startFlutterwave} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold">
                    Pay {money(order.amount, order.currency)} Securely
                  </Button>
                ) : (
                  <Notice text="Card payment is being connected. Use a bank transfer for now - contact the owner for details." />
                )}
              </div>
            )}

            {provider === "paypal" && (
              <div className="space-y-4">
                <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" aria-hidden /> PayPal or card
                </h3>
                {providerReady ? (
                  <div ref={paypalRef} aria-label="PayPal checkout buttons" />
                ) : (
                  <Notice text="PayPal is being connected. Use a bank transfer for now - contact the owner for details." />
                )}
              </div>
            )}

            {provider === "stripe" && (
              <div className="space-y-4">
                <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" aria-hidden /> Pay by card (Stripe)
                </h3>
                {providerReady ? (
                  <Button onClick={startStripe} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold">
                    Go to Secure Card Payment
                  </Button>
                ) : (
                  <Notice text="Card payment is being connected. Use a bank transfer for now - contact the owner for details." />
                )}
              </div>
            )}

            <p className="text-center text-xs text-muted-foreground inline-flex items-center gap-1.5 w-full justify-center">
              <Smartphone className="h-3.5 w-3.5" aria-hidden /> Local &amp; international payment supported
              {order.status === "pending" ? " - current status: awaiting payment" : ""}
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <p className="bg-[#FFF5F5] border-2 border-primary/30 p-4 text-sm text-neutral-700">{text}</p>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ArrowRight, BadgeCheck, ChevronRight, Clapperboard, CreditCard, Landmark, Loader2, Lock, Mail, Smartphone, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, money, type Plan, type PublicSettings, type Subscription, type StudioUser } from "@/lib/types";
import { go } from "./hash";
import { LogoMark } from "./logo";

/**
 * Subscribe - always joined to an account.
 * Step 1: create the account (or sign in / continue with Google).
 * Step 2: pick the plan and pay. There is no standalone checkout:
 * the plan is created for the signed-in user only, and the studio
 * stays locked until a plan is active.
 */

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

export function SubscribeView({
  settings,
  plans,
  preselectPlan,
  onActivated,
}: {
  settings: PublicSettings | null;
  plans: Plan[];
  preselectPlan?: string;
  /** Set when embedded in the studio gate: on a VERIFIED payment, hand control
   *  back to the studio instead of navigating. Pending/manual paths stay put. */
  onActivated?: () => void;
}) {
  const [checking, setChecking] = useState(true);
  const [user, setUser] = useState<StudioUser | null>(null);
  const [planCode, setPlanCode] = useState(preselectPlan || "");
  const [sub, setSub] = useState<Subscription | null>(null);
  const [busy, setBusy] = useState(false);
  const [phone, setPhone] = useState("");
  const paypalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<{ user: StudioUser }>("/api/user/me")
      .then((r) => setUser(r.user))
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  const plan = plans.find((p) => p.code === planCode) || null;
  const provider = settings?.paymentProvider || "manual";
  const needsKey = ["paystack", "flutterwave", "paypal"].includes(provider);
  const providerReady = !needsKey || (provider === "stripe" ? !!settings?.paymentLinkUrl : !!settings?.paymentPublicKey);

  /* ---------- step 1 → 2: payment ---------- */

  async function createSubscription(e: React.FormEvent) {
    e.preventDefault();
    if (!plan) return toast.error("Pick a plan first");
    setBusy(true);
    try {
      const res = await api<{ subscription: Subscription }>("/api/subscriptions", {
        method: "POST",
        body: JSON.stringify({ planCode: plan.code, phone, provider }),
      });
      setSub(res.subscription);
      if (provider === "paypal") initPaypalSub(res.subscription);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create subscription");
    } finally {
      setBusy(false);
    }
  }

  async function confirmPaid(reference: string) {
    if (!sub) return;
    try {
      const res = await api<{ verified: boolean; subscription: Subscription }>(
        `/api/subscriptions/${sub.id}/verify`,
        { method: "POST", body: JSON.stringify({ reference }) }
      );
      if (res.verified) {
        toast.success("Plan active - your studio is unlocked!");
        if (onActivated) onActivated();
        else go("#studio");
      } else {
        toast.message("Payment received - the owner will activate your plan shortly.");
        if (!onActivated) go("#studio");
      }
    } catch {
      toast.message("Subscription saved. Activation pending.");
      if (!onActivated) go("#studio");
    }
  }

  /* ---------- providers ---------- */

  async function startPaystack() {
    if (!sub || !settings?.paymentPublicKey) return toast.error("Payment is not set up yet - use a bank transfer for now");
    try {
      await loadScript("https://js.paystack.co/v1/inline.js", "paystack-inline");
      const w = window as PayWindow;
      if (!w.PaystackPop) throw new Error("Paystack unavailable");
      const handler = w.PaystackPop.setup({
        key: settings.paymentPublicKey,
        email: sub.email,
        amount: Math.round(sub.pricePaid * 100),
        currency: sub.currency,
        ref: sub.id,
        callback: (r) => confirmPaid(r.reference),
        onClose: () => toast.message("Payment window closed - your subscription is still saved."),
      });
      handler.openIframe();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start payment");
    }
  }

  function startFlutterwave() {
    if (!sub || !settings?.paymentPublicKey) return toast.error("Payment is not set up yet - use a bank transfer for now");
    const w = window as PayWindow;
    w.FlutterwaveCheckout?.({
      public_key: settings.paymentPublicKey,
      tx_ref: sub.id,
      amount: sub.pricePaid,
      currency: sub.currency,
      payment_options: "card,banktransfer,ussd,mobilemoneyghana,mobilemoneynigeria",
      customer: { email: sub.email, phone_number: phone, name: sub.name },
      customizations: { description: `${plan?.name || sub.planCode} plan - 1 month`.slice(0, 120) },
      callback: (data: { tx_ref?: string }) => confirmPaid(data.tx_ref || sub.id),
      onclose: () => toast.message("Payment window closed - your subscription is still saved."),
    });
  }

  function initPaypalSub(s2: Subscription) {
    if (!settings?.paymentPublicKey) return;
    loadScript(
      `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(settings.paymentPublicKey)}&currency=${s2.currency}&intent=capture`,
      "paypal-sdk"
    )
      .then(() => {
        const w = window as PayWindow;
        if (!w.paypal || !paypalRef.current) return;
        w.paypal
          .Buttons({
            style: { color: "black", label: "pay" },
            createOrder: (_d: unknown, actions: { order: { create: (o: Record<string, unknown>) => Promise<string> } }) =>
              actions.order.create({
                purchase_units: [
                  {
                    amount: { value: s2.pricePaid.toFixed(2), currency_code: s2.currency },
                    description: `${plan?.name || s2.planCode} plan subscription`.slice(0, 127),
                  },
                ],
              }),
            onApprove: async (_d: unknown, actions: { order: { capture: () => Promise<{ id: string }> } }) => {
              const details = await actions.order.capture();
              await confirmPaid(details.id || s2.id);
            },
            onError: () => toast.error("PayPal error - try again or pick another method"),
          })
          .render(paypalRef.current)
          .catch(() => toast.error("Could not render PayPal buttons"));
      })
      .catch(() => toast.error("Could not load PayPal"));
  }

  /* ---------- render ---------- */

  if (checking) {
    return (
      <section className="py-20 bg-[var(--brand-black)] text-white min-h-[70vh] grid place-items-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
      </section>
    );
  }

  const currency = settings?.currency || "USD";
  const step = sub ? 3 : user ? 2 : 1;

  return (
    <section className="py-12 md:py-20 bg-[var(--brand-black)] text-white min-h-[70vh]">
      <div className="mx-auto max-w-5xl px-4">
        <div className="text-center">
          <LogoMark className="h-10 w-10 mx-auto" aria-hidden />
          <h1 className="mt-4 text-3xl md:text-4xl font-black uppercase tracking-tight">Subscribe & Start Creating</h1>
          <p className="mt-2 text-sm text-white/60 max-w-xl mx-auto leading-relaxed">
            One flow: create your account, pick your plan, pay - and your studio unlocks.
            No subscription, no renders; every plan lives on an account.
          </p>
        </div>

        {/* steps indicator */}
        <ol className="mt-8 flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-widest" aria-label="Checkout steps">
          {["Account", "Plan", "Payment"].map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 border ${
                  step > i + 1
                    ? "border-green-500/60 text-green-400"
                    : step === i + 1
                      ? "border-primary bg-primary/15 text-white"
                      : "border-white/15 text-white/40"
                }`}
              >
                {step > i + 1 ? <BadgeCheck className="h-3.5 w-3.5" aria-hidden /> : <span>{i + 1}</span>}
                {label}
              </span>
              {i < 2 && <ChevronRight className="h-3.5 w-3.5 text-white/25" aria-hidden />}
            </li>
          ))}
        </ol>

        <div className="mt-10 grid lg:grid-cols-[1fr_360px] gap-8 items-start">
          {/* LEFT: the active step */}
          <div>
            {!user ? (
              <AccountStep onAuthed={(u) => { setUser(u); toast.success(`Welcome, ${u.name || u.email}!`); }} />
            ) : !sub ? (
              <form onSubmit={createSubscription} className="space-y-5 border border-white/15 bg-white/5 p-6" aria-label="Plan picker">
                <h2 className="font-black uppercase tracking-tight text-lg">2 - Pick your plan</h2>
                <p className="text-xs text-white/50">Signed in as <strong className="text-white/80">{user.name || user.email}</strong> - this plan will belong to your account.</p>
                <div className="space-y-2" role="radiogroup" aria-label="Plans">
                  {plans.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      role="radio"
                      aria-checked={planCode === p.code}
                      onClick={() => setPlanCode(p.code)}
                      className={`w-full text-left p-4 border-2 transition-colors ${
                        planCode === p.code ? "border-primary bg-primary/10" : "border-white/15 bg-white/5 hover:border-white/40"
                      }`}
                    >
                      <span className="flex items-center justify-between gap-3">
                        <span className="font-black tracking-tight">{p.name}</span>
                        <span className="font-black text-primary whitespace-nowrap">{money(p.priceMonthly, p.currency || currency)}<span className="text-white/40 text-xs font-bold">/mo</span></span>
                      </span>
                      <span className="block mt-1 text-xs text-white/60 leading-snug">
                        {p.maxVideosMonth} videos/month · up to {p.maxSecondsVideo}s · {p.maxResolution}{p.watermark ? " · watermark" : " · no watermark"}
                      </span>
                    </button>
                  ))}
                </div>
                <div className="space-y-2 max-w-sm">
                  <Label htmlFor="sb-phone" className="text-white/80">Phone / WhatsApp (optional)</Label>
                  <Input id="sb-phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+234 800 000 0000" className="bg-white/5 border-white/20 text-white placeholder:text-white/30" />
                </div>
                {plan && (
                  <div className="border border-primary/60 bg-primary/10 p-4 flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-widest font-bold text-white/60">You are subscribing to</p>
                      <p className="font-black text-lg">{plan.name} - monthly</p>
                    </div>
                    <p className="text-2xl font-black text-primary whitespace-nowrap">{money(plan.priceMonthly, plan.currency || currency)}</p>
                  </div>
                )}
                <Button type="submit" disabled={busy || !plan} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Clapperboard className="h-4 w-4" aria-hidden />}
                  {busy ? "Creating…" : "Continue to payment"}
                </Button>
                <p className="text-center text-xs text-white/40">Billed monthly · cancel anytime · no renders without an active plan.</p>
              </form>
            ) : (
              <div className="space-y-6">
                <div className="border-2 border-primary p-5 bg-primary/5">
                  <p className="text-xs uppercase tracking-widest font-bold text-white/60">3 - Payment</p>
                  <p className="font-mono font-black text-lg mt-1">{sub.id.slice(0, 10).toUpperCase()}</p>
                  <p className="mt-2 text-sm text-white/70">
                    {plan?.name || sub.planCode} plan for <strong>{sub.name}</strong> -{" "}
                    <span className="font-black text-primary">{money(sub.pricePaid, sub.currency)}</span>
                  </p>
                </div>

                {provider === "manual" && (
                  <div className="space-y-4">
                    <h3 className="font-black text-lg uppercase inline-flex items-center gap-2">
                      <Landmark className="h-5 w-5 text-primary" aria-hidden /> Pay by bank / mobile money
                    </h3>
                    {settings?.bankDetails ? (
                      <pre className="bg-white/5 border border-white/15 p-4 text-sm whitespace-pre-wrap font-sans">{settings.bankDetails}</pre>
                    ) : null}
                    <p className="text-sm text-white/60 leading-relaxed">{settings?.paymentInstructions}</p>
                    <Button
                      onClick={() => {
                        toast.message("Saved! The owner activates your plan as soon as the payment lands.");
                        if (!onActivated) go("#studio");
                      }}
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
                        Pay {money(sub.pricePaid, sub.currency)} Securely
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
                        Pay {money(sub.pricePaid, sub.currency)} Securely
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
                      <Button onClick={() => { if (settings?.paymentLinkUrl) window.location.href = settings.paymentLinkUrl; }} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold">
                        Go to Secure Card Payment
                      </Button>
                    ) : (
                      <Notice text="Card payment is being connected. Use a bank transfer for now - contact the owner for details." />
                    )}
                  </div>
                )}

                <p className="text-center text-xs text-white/40 inline-flex items-center gap-1.5 w-full justify-center">
                  <Smartphone className="h-3.5 w-3.5" aria-hidden /> Local & international payment supported
                </p>
              </div>
            )}
          </div>

          {/* RIGHT: order summary rail */}
          <aside className="space-y-4 lg:sticky lg:top-8">
            <div className="border border-white/15 bg-white/5 p-5">
              <p className="text-xs font-black uppercase tracking-widest text-white/50">Your order</p>
              {plan ? (
                <>
                  <p className="mt-2 text-xl font-black">{plan.name}</p>
                  <p className="text-xs text-white/60 mt-1 leading-relaxed">{plan.blurb}</p>
                  <p className="mt-3 text-2xl font-black text-primary">
                    {money(plan.priceMonthly, plan.currency || currency)}
                    <span className="text-xs text-white/40 font-bold"> /month</span>
                  </p>
                  <ul className="mt-3 space-y-1.5 text-xs text-white/60">
                    <li>· {plan.maxVideosMonth} videos every month</li>
                    <li>· Up to {plan.maxSecondsVideo}s per video</li>
                    <li>· Renders at {plan.maxResolution}</li>
                    <li>· {plan.watermark ? "DeYoung watermark" : "No watermark"}</li>
                  </ul>
                </>
              ) : (
                <p className="mt-2 text-sm text-white/60">Pick a plan on the left to see the summary here.</p>
              )}
            </div>
            <div className="border border-white/15 bg-white/5 p-5">
              <p className="text-xs font-black uppercase tracking-widest text-white/50">Why an account?</p>
              <ul className="mt-3 space-y-2 text-xs text-white/60 leading-relaxed">
                <li className="flex gap-2"><Lock className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" aria-hidden /> Your plan, quota and queue live on your account - no shared checkout links.</li>
                <li className="flex gap-2"><BadgeCheck className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" aria-hidden /> Your renders, licensed voices and support chat stay in one studio.</li>
                <li className="flex gap-2"><ArrowRight className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" aria-hidden /> Subscribe while registering - it takes under a minute.</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Step 1: account ---------------- */

function AccountStep({ onAuthed }: { onAuthed: (u: StudioUser) => void }) {
  const [mode, setMode] = useState<"signup" | "signin">("signup");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [googleReady, setGoogleReady] = useState(false);

  useEffect(() => {
    api<{ configured: boolean }>("/api/auth/google/status")
      .then((r) => setGoogleReady(r.configured === true))
      .catch(() => setGoogleReady(false));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const url = mode === "signin" ? "/api/user/login" : "/api/user/register";
      const body =
        mode === "signin"
          ? { email: form.email, password: form.password }
          : { name: form.name, email: form.email, password: form.password };
      const res = await api<{ user: StudioUser }>(url, { method: "POST", body: JSON.stringify(body) });
      onAuthed(res.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const nextParam = encodeURIComponent("/#subscribe");

  return (
    <div className="border border-white/15 bg-white/5 p-6">
      <h2 className="font-black uppercase tracking-tight text-lg">1 - Your account</h2>
      <p className="mt-1 text-xs text-white/50">
        {mode === "signup"
          ? "Create it now - your plan attaches straight to it."
          : "Sign in and we'll attach the plan to your account."}
      </p>

      <form onSubmit={submit} className="mt-5 space-y-4">
        {mode === "signup" && (
          <div className="space-y-2">
            <Label htmlFor="sb-name" className="text-white/80">Name</Label>
            <div className="relative">
              <UserIcon className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
              <Input id="sb-name" required value={form.name} autoComplete="name"
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Your name"
                className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
            </div>
          </div>
        )}
        <div className="space-y-2">
          <Label htmlFor="sb-email" className="text-white/80">Email</Label>
          <div className="relative">
            <Mail className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
            <Input id="sb-email" type="email" required value={form.email} autoComplete="email"
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@example.com"
              className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="sb-pass" className="text-white/80">Password</Label>
          <div className="relative">
            <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
            <Input id="sb-pass" type="password" required value={form.password}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
              className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
          </div>
        </div>

        {error && <p className="text-sm text-primary font-semibold" role="alert">{error}</p>}

        <Button type="submit" disabled={busy} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base">
          {busy ? "One moment…" : mode === "signin" ? "Sign in & continue" : "Create account & continue"}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Button>

        {googleReady && (
          <>
            <div className="flex items-center gap-3" aria-hidden>
              <span className="h-px flex-1 bg-white/15" />
              <span className="text-[10px] font-black uppercase tracking-widest text-white/40">or</span>
              <span className="h-px flex-1 bg-white/15" />
            </div>
            <a
              href={`/api/auth/google/start?next=${nextParam}`}
              className="flex h-12 w-full items-center justify-center gap-3 bg-white text-[#1F1F1F] text-sm font-bold hover:bg-white/90 transition-colors"
              aria-label="Continue with Google"
            >
              <GoogleG />
              Continue with Google
            </a>
          </>
        )}

        <p className="text-center text-sm text-white/60">
          {mode === "signup" ? "Already have an account?" : "New to DeYoung?"}{" "}
          <button
            type="button"
            onClick={() => { setMode(mode === "signup" ? "signin" : "signup"); setError(""); }}
            className="font-bold text-primary hover:underline underline-offset-4"
          >
            {mode === "signup" ? "Sign in" : "Create one"}
          </button>
        </p>
        <p className="text-center text-[11px] text-white/40 leading-relaxed">
          By continuing you agree to our{" "}
          <a href="#terms" className="underline underline-offset-2 hover:text-white">Terms</a> and{" "}
          <a href="#privacy" className="underline underline-offset-2 hover:text-white">Privacy Policy</a>.
        </p>
      </form>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return <p className="bg-white/5 border border-primary/40 p-4 text-sm text-white/70">{text}</p>;
}

/** Google "G" - the standard four-colour mark used on sign-in buttons. */
function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden className="shrink-0">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

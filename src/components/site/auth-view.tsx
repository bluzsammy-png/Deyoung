"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/types";
import { go } from "@/components/site/hash";
import { Chrome, Clapperboard, Loader2, LogIn, ShieldCheck, UserPlus } from "lucide-react";

/* Shared cinematic shell for the auth views. */
function AuthShell({
  kicker,
  title,
  subtitle,
  children,
  footer,
}: {
  kicker: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] text-white">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 md:grid-cols-2 md:py-20">
        <div className="hidden md:flex flex-col justify-center">
          <div className="flex items-center gap-2 text-primary">
            <Clapperboard className="h-5 w-5" aria-hidden />
            <span className="text-sm font-black uppercase tracking-[0.2em]">{kicker}</span>
          </div>
          <h1 className="mt-4 text-4xl font-black uppercase leading-[1.05] xl:text-5xl">{title}</h1>
          <p className="mt-4 max-w-md text-white/60">{subtitle}</p>
          <ul className="mt-8 space-y-3 text-sm text-white/70">
            {[
              "AI Film Studio — storyboard, script writer, prompt enhancer",
              "GPU life meter that works like a real film simulator",
              "Up to 60-second renders in a single pass",
            ].map((t) => (
              <li key={t} className="flex items-start gap-2">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:p-8">
          {children}
        </div>
      </div>
      {footer}
    </div>
  );
}

function GoogleButton({ label }: { label: string }) {
  return (
    <Button
      asChild
      variant="outline"
      className="w-full border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
    >
      <a href="/api/auth/google">
        <Chrome className="h-4 w-4" aria-hidden />
        {label}
      </a>
    </Button>
  );
}

const GOOGLE_SETUP_HINT =
  "Google sign-in is not configured yet. The owner adds GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (redirect URI: <origin>/api/auth/google/callback) to unlock one-tap login.";

/* ------------------------------- Sign in ------------------------------- */

export function SignInView({ error }: { error?: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(
    error === "google_unconfigured"
      ? GOOGLE_SETUP_HINT
      : error === "google_state"
        ? "That Google link expired — try again."
        : error === "google_exchange"
          ? "Google could not verify the account — try again."
          : error
            ? decodeURIComponent(error)
            : null
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api("/api/auth/user-login", { method: "POST", body: JSON.stringify({ email, password }) });
      go("/dashboard");
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      kicker="Welcome back"
      title="Sign in to the studio."
      subtitle="Your renders, your GPU life, your storyboard — exactly where you left them."
      footer={null}
    >
      <h2 className="text-xl font-black uppercase">Sign in</h2>
      <p className="mt-1 text-sm text-white/50">Pick up where you left off.</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="si-email" className="text-white/70">Email</Label>
          <Input
            id="si-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="si-password" className="text-white/70">Password</Label>
          <Input
            id="si-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
          />
        </div>
        {err && <p className="text-sm font-semibold text-red-400">{err}</p>}
        <Button type="submit" disabled={busy} className="w-full bg-primary font-bold text-white hover:bg-[#B91C1C]">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <LogIn className="h-4 w-4" aria-hidden />}
          Sign in
        </Button>
      </form>
      <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-widest text-white/30">
        <span className="h-px flex-1 bg-white/10" /> or <span className="h-px flex-1 bg-white/10" />
      </div>
      <GoogleButton label="Continue with Google" />
      <p className="mt-6 text-sm text-white/50">
        New here?{" "}
        <a href="#/signup" className="font-bold text-primary hover:underline">
          Create an account
        </a>{" "}
        — your subscription starts with it.
      </p>
    </AuthShell>
  );
}

/* ------------------------------- Sign up ------------------------------- */

export function SignUpView({ planCode }: { planCode?: string }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api("/api/auth/signup", { method: "POST", body: JSON.stringify({ name, email, password }) });
      // subscription goes with the registration: straight into the checkout funnel
      go(planCode ? `/subscribe?plan=${encodeURIComponent(planCode)}` : "/subscribe");
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Sign up failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      kicker="Join DeYoung"
      title="One account. Studio, renders, GPU life."
      subtitle="Create your account, pick a plan, and the AI Film Studio unlocks — subscription is part of signing up."
      footer={null}
    >
      <h2 className="text-xl font-black uppercase">Create your account</h2>
      <p className="mt-1 text-sm text-white/50">Step 1 of 2 — then choose your plan.</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="su-name" className="text-white/70">Name</Label>
          <Input
            id="su-name"
            autoComplete="name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ada Obi"
            className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="su-email" className="text-white/70">Email</Label>
          <Input
            id="su-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="su-password" className="text-white/70">Password</Label>
          <Input
            id="su-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
            className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
          />
        </div>
        {err && <p className="text-sm font-semibold text-red-400">{err}</p>}
        <Button type="submit" disabled={busy} className="w-full bg-primary font-bold text-white hover:bg-[#B91C1C]">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <UserPlus className="h-4 w-4" aria-hidden />}
          Create account &amp; choose plan
        </Button>
      </form>
      <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-widest text-white/30">
        <span className="h-px flex-1 bg-white/10" /> or <span className="h-px flex-1 bg-white/10" />
      </div>
      <GoogleButton label="Sign up with Google" />
      <p className="mt-6 text-sm text-white/50">
        Already have an account?{" "}
        <a href="#/signin" className="font-bold text-primary hover:underline">
          Sign in
        </a>
      </p>
    </AuthShell>
  );
}

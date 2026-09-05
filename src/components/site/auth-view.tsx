"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Lock, Mail, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type StudioUser } from "@/lib/types";
import { LogoMark } from "./logo";

/**
 * Sign in / create account for DeYoung customer accounts.
 * The same view serves both modes; `onAuthed` receives the fresh profile.
 * Google Sign-In appears only when the operator has configured the OAuth
 * credentials (server reports /api/auth/google/status).
 */
export function AuthView({ onAuthed }: { onAuthed: (u: StudioUser) => void }) {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [googleReady, setGoogleReady] = useState(false);
  const [googleError, setGoogleError] = useState("");

  useEffect(() => {
    api<{ configured: boolean }>("/api/auth/google/status")
      .then((r) => setGoogleReady(r.configured === true))
      .catch(() => setGoogleReady(false));
    // error passed back by the Google callback
    const q = new URLSearchParams(window.location.search);
    const ge = q.get("google_error");
    if (ge) {
      setGoogleError(
        ge === "unverified"
          ? "Google reported that email as unverified - sign in with your password instead."
          : ge === "state"
            ? "Sign-in session expired - try Google sign-in again."
            : "Google sign-in did not complete - try again or use your password."
      );
      window.history.replaceState(null, "", window.location.pathname + "#studio");
    }
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

  return (
    <div className="min-h-[70vh] bg-[var(--brand-black)] text-white flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-md">
        <div className="text-center">
          <LogoMark className="h-12 w-12 mx-auto" aria-hidden />
          <h1 className="mt-4 text-3xl font-black uppercase tracking-tight">
            {mode === "signin" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="mt-2 text-sm text-white/60">
            {mode === "signin"
              ? "Sign in to your studio - queue, renders and support, all in one place."
              : "Ten seconds to create - then pick your plan and your studio comes alive."}
          </p>
        </div>

        <form onSubmit={submit} className="mt-8 space-y-4 border border-white/15 bg-white/5 p-6">
          {mode === "signup" && (
            <div className="space-y-2">
              <Label htmlFor="a-name" className="text-white/80">Name</Label>
              <div className="relative">
                <UserIcon className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
                <Input
                  id="a-name" required value={form.name} autoComplete="name"
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Your name"
                  className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
                />
              </div>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="a-email" className="text-white/80">Email</Label>
            <div className="relative">
              <Mail className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
              <Input
                id="a-email" type="email" required value={form.email} autoComplete="email"
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@example.com"
                className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="a-pass" className="text-white/80">Password</Label>
            <div className="relative">
              <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" aria-hidden />
              <Input
                id="a-pass" type="password" required value={form.password}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
                className="pl-9 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-primary font-semibold" role="alert">{error}</p>
          )}

          <Button
            type="submit" disabled={busy}
            className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
          >
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
                href="/api/auth/google/start"
                className="flex h-12 w-full items-center justify-center gap-3 bg-white text-[#1F1F1F] text-sm font-bold hover:bg-white/90 transition-colors"
                aria-label="Continue with Google"
              >
                <GoogleG />
                Continue with Google
              </a>
            </>
          )}

          {googleError && <p className="text-sm text-primary font-semibold" role="alert">{googleError}</p>}

          <p className="text-center text-sm text-white/60">
            {mode === "signin" ? "New to DeYoung?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); }}
              className="font-bold text-primary hover:underline underline-offset-4"
            >
              {mode === "signin" ? "Create an account" : "Sign in"}
            </button>
          </p>
          <p className="text-center text-[11px] text-white/40 leading-relaxed">
            By continuing you agree to our{" "}
            <a href="#terms" className="underline underline-offset-2 hover:text-white">Terms</a> and{" "}
            <a href="#privacy" className="underline underline-offset-2 hover:text-white">Privacy Policy</a>.
            Your password is stored only as a scrypt hash - we can&apos;t read it.
          </p>
        </form>
      </div>
    </div>
  );
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

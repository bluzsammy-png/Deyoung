"use client";

import { useEffect, useState } from "react";
import { Menu, X, Clapperboard, LogOut, LayoutDashboard, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LogoMark } from "./logo";
import { go } from "./hash";
import { signOutUser, useSessionBadge } from "./use-session";
import type { PublicSettings } from "@/lib/types";

const LINKS = [
  { label: "Video Plans", href: "#plans" },
  { label: "Services", href: "#services" },
  { label: "Premieres", href: "#premieres" },
  { label: "Work", href: "#gallery" },
  { label: "About", href: "#about" },
  { label: "FAQ", href: "#faq" },
  { label: "Contact", href: "#contact" },
];

export function SiteHeader({ settings }: { settings: PublicSettings | null }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const session = useSessionBadge();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const name = settings?.siteName || "DeYoung";
  const user = session?.user ?? null;
  const admin = session?.admin ?? null;

  async function handleSignOut() {
    await signOutUser();
    setOpen(false);
    go("#/");
    window.location.reload(); // re-render every section with the fresh session
  }

  const authButtons = user ? (
    <>
      <Button
        onClick={() => go("#dashboard")}
        className="hidden sm:inline-flex border border-white/15 bg-white/5 font-bold text-neutral-900 hover:bg-white/10"
        variant="outline"
      >
        <LayoutDashboard className="h-4 w-4" aria-hidden />
        Dashboard
      </Button>
      <Button
        onClick={handleSignOut}
        variant="outline"
        className="hidden sm:inline-flex border-white/15 bg-white/5 text-neutral-700 hover:bg-white/10 hover:text-neutral-900"
        aria-label={`Sign out ${user.email}`}
      >
        <LogOut className="h-4 w-4" aria-hidden />
        Sign out
      </Button>
    </>
  ) : (
    <Button
      onClick={() => go("#signin")}
      variant="outline"
      className="hidden sm:inline-flex border-white/15 bg-white/5 font-bold text-neutral-700 hover:bg-white/10 hover:text-neutral-900"
    >
      <LogIn className="h-4 w-4" aria-hidden />
      Sign in
    </Button>
  );

  return (
    <header
      className={`sticky top-0 z-50 bg-white/85 backdrop-blur-xl border-b transition-all ${
        scrolled ? "shadow-[0_1px_0_0_#DC2626] bg-white/95" : "border-border"
      }`}
    >
      <div className="mx-auto max-w-6xl px-4 h-16 flex items-center justify-between gap-4">
        <a
          href="#"
          className="flex items-center gap-2 font-black tracking-tight text-xl"
          aria-label={`${name} — home`}
        >
          <LogoMark className="h-7 w-7 drop-shadow-[0_2px_6px_rgba(220,38,38,0.35)]" />
          <span className="uppercase">{name}</span>
        </a>

        <nav aria-label="Main" className="hidden md:flex items-center gap-6">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm font-semibold text-neutral-700 hover:text-primary transition-colors"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {authButtons}
          <Button
            onClick={() => go("#subscribe")}
            className="hidden sm:inline-flex bg-primary hover:bg-[#B91C1C] text-white font-bold"
          >
            <Clapperboard className="h-4 w-4" aria-hidden />
            Subscribe
          </Button>
          <button
            className="md:hidden p-2 -mr-2"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {open && (
        <nav aria-label="Mobile" className="md:hidden border-t bg-white px-4 pb-4 pt-2">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block py-3 font-semibold border-b last:border-0"
            >
              {l.label}
            </a>
          ))}
          {user ? (
            <>
              <Button
                onClick={() => {
                  setOpen(false);
                  go("#dashboard");
                }}
                className="mt-3 w-full bg-primary hover:bg-[#B91C1C] text-white font-bold"
              >
                <LayoutDashboard className="h-4 w-4" aria-hidden />
                Dashboard &amp; Studio
              </Button>
              <Button
                onClick={handleSignOut}
                variant="outline"
                className="mt-2 w-full border-neutral-200 text-neutral-700"
              >
                <LogOut className="h-4 w-4" aria-hidden />
                Sign out
              </Button>
            </>
          ) : (
            <Button
              onClick={() => {
                setOpen(false);
                go("#signin");
              }}
              variant="outline"
              className="mt-3 w-full border-neutral-200 text-neutral-700 font-bold"
            >
              <LogIn className="h-4 w-4" aria-hidden />
              Sign in
            </Button>
          )}
          <Button
            onClick={() => {
              setOpen(false);
              go("#subscribe");
            }}
            className="mt-2 w-full bg-primary hover:bg-[#B91C1C] text-white font-bold"
          >
            Subscribe
          </Button>
          {admin && (
            <p className="mt-2 text-center text-xs font-bold uppercase tracking-widest text-primary">
              Owner signed in · {admin.email}
            </p>
          )}
        </nav>
      )}
    </header>
  );
}

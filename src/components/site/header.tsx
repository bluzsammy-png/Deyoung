"use client";

import { useEffect, useState } from "react";
import { LogOut, Menu, X, Clapperboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type StudioUser } from "@/lib/types";
import { LogoMark } from "./logo";
import { go } from "./hash";
import type { PublicSettings } from "@/lib/types";

const LINKS = [
  { label: "Video Plans", href: "#plans" },
  { label: "Services", href: "#services" },
  { label: "Work", href: "#gallery" },
  { label: "About", href: "#about" },
  { label: "FAQ", href: "#faq" },
  { label: "Contact", href: "#contact" },
];

export function SiteHeader({ settings }: { settings: PublicSettings | null }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [user, setUser] = useState<StudioUser | null>(null);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    api<{ user: StudioUser }>("/api/user/me")
      .then((r) => setUser(r.user))
      .catch(() => setUser(null));
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  async function signOut() {
    setMenu(false);
    await api("/api/user/logout", { method: "POST" }).catch(() => {});
    setUser(null);
    go("#");
  }

  const name = settings?.siteName || "DeYoung";

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
          aria-label={`${name} - home`}
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
          <a
            href="#studio"
            className="text-sm font-black uppercase tracking-widest text-primary hover:text-[#B91C1C] transition-colors"
          >
            Studio
          </a>
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenu((v) => !v)}
                className="h-9 w-9 grid place-items-center bg-[var(--brand-black)] text-white font-black uppercase"
                aria-label="Your account menu"
                aria-expanded={menu}
              >
                {(user.name || user.email).slice(0, 1).toUpperCase()}
              </button>
              {menu && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-white border-2 border-[var(--brand-black)] shadow-xl py-1 z-50">
                  <a href="#studio" onClick={() => setMenu(false)} className="block px-4 py-2.5 text-sm font-bold hover:bg-neutral-100">
                    Your Studio
                  </a>
                  <a href="#studio" onClick={() => setMenu(false)} className="block px-4 py-2.5 text-sm text-neutral-600 hover:bg-neutral-100">
                    Profile &amp; plan
                  </a>
                  <button
                    onClick={signOut}
                    className="w-full text-left px-4 py-2.5 text-sm font-bold text-primary hover:bg-neutral-100 inline-flex items-center gap-2"
                  >
                    <LogOut className="h-4 w-4" aria-hidden /> Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <a href="#studio" className="hidden sm:inline-flex">
              <Button variant="outline" className="border-[var(--brand-black)] text-[var(--brand-black)] hover:bg-[var(--brand-black)] hover:text-white font-bold">
                Sign in
              </Button>
            </a>
          )}
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
          <a
            href="#studio"
            onClick={() => setOpen(false)}
            className="block py-3 font-black uppercase tracking-widest text-primary border-b"
          >
            Studio - sign in / create account
          </a>
          <Button
            onClick={() => {
              setOpen(false);
              go("#subscribe");
            }}
            className="mt-3 w-full bg-primary hover:bg-[#B91C1C] text-white font-bold"
          >
            Subscribe
          </Button>
        </nav>
      )}
    </header>
  );
}

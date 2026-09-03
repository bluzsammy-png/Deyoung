"use client";

import { useEffect, useState } from "react";
import { Menu, X, Clapperboard } from "lucide-react";
import { Button } from "@/components/ui/button";
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

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const name = settings?.siteName || "DeYoung";

  return (
    <header
      className={`sticky top-0 z-50 bg-white/95 backdrop-blur border-b transition-shadow ${
        scrolled ? "shadow-[0_1px_0_0_#DC2626]" : "border-border"
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

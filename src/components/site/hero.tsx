"use client";

import Image from "next/image";
import { ArrowRight, Clock, ShieldCheck, BadgeCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { go } from "./hash";
import type { PublicSettings } from "@/lib/types";

export function Hero({ settings }: { settings: PublicSettings | null }) {
  const s = settings;
  const name = s?.heroTitle || "DEYOUNG";
  const photo = s?.ownerPhotoUrl || "/img/avatar-default.png";

  return (
    <section className="bg-[var(--brand-black)] text-white relative overflow-hidden">
      <div className="absolute inset-0 dy-hero-grid" aria-hidden />
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary" aria-hidden />

      <div className="relative mx-auto max-w-6xl px-4 pt-14 pb-16 md:pt-24 md:pb-24 grid md:grid-cols-[1.2fr_1fr] gap-10 items-center">
        <div>
          <p className="inline-flex items-center gap-2 text-xs font-bold tracking-[0.25em] uppercase text-white/70 border border-white/20 px-3 py-1.5">
            <span className="h-2 w-2 bg-primary inline-block" aria-hidden />
            {s?.tagline || "Bold work. Real results."}
          </p>

          <h1 className="mt-5 text-6xl sm:text-7xl md:text-8xl font-black tracking-tighter leading-[0.9] uppercase">
            {name.split(" ").map((word, i) => (
              <span key={i} className={i === 0 ? "text-white" : "text-primary"}>
                {word}{" "}
              </span>
            ))}
          </h1>

          <p className="mt-5 max-w-xl text-base md:text-lg text-white/70 leading-relaxed">
            {s?.heroSubtitle ||
              "AI video generation up to 60 seconds in one pass — where other models stop at 15. Plus bold creative services. Subscribe or book online, paid your way (local or international)."}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button
              onClick={() => go("#plans")}
              className="h-12 px-6 text-base font-bold bg-primary hover:bg-[#B91C1C] text-white"
            >
              60-Second AI Video — See Plans <ArrowRight className="h-4 w-4" aria-hidden />
            </Button>
            <a href="#gallery">
              <Button
                variant="outline"
                className="h-12 px-6 text-base font-bold border-white/30 bg-transparent text-white hover:bg-white hover:text-black"
              >
                See the Work
              </Button>
            </a>
            <a href="#book">
              <Button
                variant="outline"
                className="h-12 px-6 text-base font-bold border-white/30 bg-transparent text-white hover:bg-white hover:text-black"
              >
                Book a Service
              </Button>
            </a>
          </div>

          <ul className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl">
            {[
              { icon: Clock, text: "Up to 60 seconds in one pass — others stop at 15." },
              { icon: ShieldCheck, text: "Pay local or international — bank, mobile money or card." },
              { icon: BadgeCheck, text: s?.responseTime || "Replies within 24 hours." },
            ].map(({ icon: Icon, text }, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/60">
                <Icon className="h-4 w-4 mt-0.5 text-primary shrink-0" aria-hidden />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto w-full max-w-xs md:max-w-sm">
          <div className="absolute -top-3 -left-3 right-3 bottom-3 bg-primary" aria-hidden />
          <div className="absolute -bottom-3 -right-3 left-3 top-3 border-2 border-white/20" aria-hidden />
          <div className="relative aspect-square overflow-hidden bg-neutral-900">
            <Image
              src={photo}
              alt={`${s?.ownerName || "DeYoung"} — ${s?.ownerTitle || "creative professional"}, portrait`}
              fill
              sizes="(max-width: 768px) 80vw, 33vw"
              className="object-cover"
              priority
            />
          </div>
          <div className="relative -mt-6 ml-4 inline-flex items-center gap-2 bg-white text-black font-bold text-sm px-4 py-2 shadow-lg">
            <span className="h-2.5 w-2.5 bg-primary" aria-hidden />
            {s?.ownerName || "DeYoung"} — {s?.ownerTitle || "Creative Professional"}
          </div>
        </div>
      </div>

      <div className="relative mx-auto max-w-6xl px-4 pb-14">
        <p className="mb-3 inline-flex items-center gap-2 text-xs font-bold tracking-[0.25em] uppercase text-white/70">
          <span className="h-2 w-2 bg-primary inline-block" aria-hidden />
          Watch the 60-second film — Amara &amp; Kojo
        </p>
        <video
          src="/video/deyoung-film-web.mp4"
          poster="/img/film-poster.jpg"
          controls
          muted
          loop
          playsInline
          preload="metadata"
          className="w-full aspect-video bg-black border border-white/15"
          aria-label="DeYoung 60-second AI film trailer"
        />
      </div>

      <div className="relative h-2 dy-stripes opacity-40" aria-hidden />
    </section>
  );
}

/** Fixed bottom CTA — mobile only. */
export function StickyMobileCta({ whatsapp }: { whatsapp?: string }) {
  return (
    <div className="fixed bottom-0 inset-x-0 z-40 sm:hidden dy-safe-bottom">
      <div className="bg-[var(--brand-black)] text-white px-4 py-3 flex items-center gap-3 shadow-[0_-4px_20px_rgba(0,0,0,0.35)]">
        <div className="flex-1 leading-tight">
          <p className="text-[11px] uppercase tracking-widest text-white/50 font-bold">Ready when you are</p>
          <p className="text-sm font-bold">Book in under 2 minutes</p>
        </div>
        {whatsapp ? (
          <a
            href={`https://wa.me/${whatsapp.replace(/[^\d]/g, "")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-bold border border-white/30 px-3 py-2"
          >
            Chat
          </a>
        ) : null}
        <button
          onClick={() => go("#book")}
          className="bg-primary hover:bg-[#B91C1C] text-sm font-bold px-4 py-2"
        >
          Book Now
        </button>
      </div>
    </div>
  );
}

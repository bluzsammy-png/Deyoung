"use client";

import { useEffect, useRef } from "react";
import { ArrowRight, Clock, ShieldCheck, BadgeCheck, Play, ChevronDown, Flame, Clapperboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { go } from "./hash";
import { TiltCard } from "./motion";
import { ShowReel } from "./showreel";
import type { PublicSettings } from "@/lib/types";

export function Hero({ settings }: { settings: PublicSettings | null }) {
  const s = settings;
  const name = s?.heroTitle || "DEYOUNG";
  const sceneRef = useRef<HTMLDivElement>(null);

  /* Pointer parallax - subtle depth on desktop only. */
  useEffect(() => {
    if (window.matchMedia("(hover: none)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      const x = e.clientX / window.innerWidth - 0.5;
      const y = e.clientY / window.innerHeight - 0.5;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        sceneRef.current?.querySelectorAll<HTMLElement>("[data-depth]").forEach((el) => {
          const d = Number(el.dataset.depth || 0);
          el.style.transform = `translate3d(${(x * d).toFixed(1)}px, ${(y * d).toFixed(1)}px, 0)`;
        });
      });
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <section className="bg-[var(--brand-black)] text-white relative overflow-hidden dy-vignette">
      {/* ambient layers */}
      <div className="absolute inset-0 dy-hero-grid" aria-hidden />
      <div
        className="dy-orb absolute -top-24 -left-24 h-96 w-96 rounded-full bg-[#DC2626]/25"
        aria-hidden
      />
      <div
        className="dy-orb absolute top-1/3 -right-32 h-[28rem] w-[28rem] rounded-full bg-[#991B1B]/30"
        style={{ animationDelay: "-8s" }}
        aria-hidden
      />
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary" aria-hidden />

      <div
        ref={sceneRef}
        className="dy-scene relative mx-auto max-w-6xl px-4 pt-16 pb-14 md:pt-24 md:pb-20 grid md:grid-cols-[1.15fr_1fr] gap-12 items-center"
      >
        {/* ---- copy ---- */}
        <div>
          <div className="dy-ticket max-w-full">
            <div className="dy-ticket-inner flex-wrap justify-center text-center gap-x-3 gap-y-1.5 max-w-full">
              <span className="dy-ticket-shine" aria-hidden />
              <span className="inline-flex items-center gap-1.5 bg-primary text-white text-[10px] font-black uppercase tracking-[0.2em] px-2.5 py-1">
                <Clapperboard className="h-3 w-3" aria-hidden /> DeYoung Original
              </span>
              <p className="text-xs font-black tracking-[0.28em] uppercase text-white sm:whitespace-nowrap">
                {s?.tagline || "Bold work. Real results."}
              </p>
              <span className="dy-ticket-stars hidden lg:inline whitespace-nowrap" aria-hidden>
                60S · 6 STYLES · HD
              </span>
            </div>
          </div>

          <h1 className="mt-6 text-6xl sm:text-7xl md:text-8xl font-black tracking-tighter leading-[0.9] uppercase">
            {(() => {
              const words = name.split(" ").filter(Boolean);
              if (words.length > 1) {
                return words.map((word, i) => (
                  <span key={i} className={i === 0 ? "text-white" : "dy-grad-text"}>
                    {word}{" "}
                  </span>
                ));
              }
              // single-word brand: split half white / half gradient
              const w = words[0] || "DEYOUNG";
              const cut = Math.max(1, Math.floor(w.length / 2));
              return (
                <>
                  <span className="text-white">{w.slice(0, cut)}</span>
                  <span className="dy-grad-text">{w.slice(cut)}</span>
                </>
              );
            })()}
          </h1>

          <p className="mt-6 max-w-xl text-base md:text-lg text-white/70 leading-relaxed">
            {s?.heroSubtitle ||
              "AI video generation up to 60 seconds in one pass, where other models stop at 15. Plus bold creative services. Subscribe or book online, paid your way (local or international)."}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button
              onClick={() => go("#plans")}
              className="h-12 px-6 text-base font-bold bg-primary hover:bg-[#B91C1C] text-white dy-glow-red"
            >
              60-Second AI Video: See Plans <ArrowRight className="h-4 w-4" aria-hidden />
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

          <button
            onClick={() => go("#plans")}
            className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-primary hover:text-white transition-colors"
          >
            <Flame className="h-4 w-4" aria-hidden />
            Prices just went up: lock your rate before the next rise
          </button>

          <ul className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl">
            {[
              { icon: Clock, text: "Up to 60 seconds in one pass. Others stop at 15." },
              { icon: ShieldCheck, text: "Pay local or international: bank, mobile money or card." },
              { icon: BadgeCheck, text: s?.responseTime || "Replies within 24 hours." },
            ].map(({ icon: Icon, text }, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/60">
                <Icon className="h-4 w-4 mt-0.5 text-primary shrink-0" aria-hidden />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* ---- 3D showreel scene (was: static DY portrait) ---- */}
        <div className="relative mx-auto w-full max-w-xs md:max-w-sm">
          <div
            data-depth="14"
            className="absolute -top-6 right-0 z-20 dy-glass rounded-xl px-4 py-3 dy-float"
          >
            <p className="text-2xl font-black leading-none dy-grad-text">60s</p>
            <p className="text-[10px] font-bold tracking-widest text-white/60 uppercase mt-1">
              One pass
            </p>
          </div>
          <div
            data-depth="10"
            className="absolute -bottom-12 -right-4 z-20 dy-glass rounded-xl px-4 py-3 dy-float"
            style={{ animationDelay: "-3.5s" }}
          >
            <p className="text-2xl font-black leading-none text-white">5</p>
            <p className="text-[10px] font-bold tracking-widest text-white/60 uppercase mt-1">
              Styles
            </p>
          </div>

          <TiltCard max={9} lift={10} className="relative">
            <div className="absolute -top-3 -left-3 right-3 bottom-3 bg-primary" aria-hidden />
            <div className="absolute -bottom-3 -right-3 left-3 top-3 border-2 border-white/20" aria-hidden />
            <div className="relative">
              <ShowReel />
            </div>
            <div className="relative mt-2 ml-0 inline-flex items-center gap-2 bg-white text-black font-bold text-sm px-4 py-2 shadow-lg z-20 sm:-mt-6 sm:ml-4">
              <span className="h-2.5 w-2.5 bg-primary" aria-hidden />
              {s?.ownerName || "DeYoung"} · {s?.ownerTitle || "Creative Professional"}
            </div>
          </TiltCard>
        </div>
      </div>

      {/* ---- film band ---- */}
      <div className="relative mx-auto max-w-6xl px-4 pb-16" data-depth="6">
        <p className="mb-3 inline-flex items-center gap-2 text-xs font-bold tracking-[0.25em] uppercase text-white/70">
          <span className="h-2 w-2 bg-primary inline-block" aria-hidden />
          Watch the film: the cast actually talks
        </p>
        <TiltCard max={4} lift={8} className="group relative">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-[#DC2626] via-[#7F1D1D] to-[#DC2626] opacity-60 blur-[6px] rounded-sm" aria-hidden />
          <div className="relative border border-white/15 bg-black">
            <video
              src="/video/deyoung-film-web.mp4?v=8"
              poster="/img/film-poster.jpg?v=8"
              controls
              loop
              playsInline
              preload="metadata"
              className="w-full aspect-video"
              aria-label="DeYoung campaign film: 84 seconds, the cast talks"
            />
            <span className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="dy-glass rounded-full h-16 w-16 flex items-center justify-center">
                <Play className="h-6 w-6 text-white fill-white" aria-hidden />
              </span>
            </span>
          </div>
        </TiltCard>
      </div>

      <div className="relative pb-8 flex justify-center text-white/40" aria-hidden>
        <a href="#plans" aria-label="Scroll to plans">
          <ChevronDown className="h-6 w-6 animate-bounce" />
        </a>
      </div>

      <div className="relative h-2 dy-stripes opacity-40" aria-hidden />
    </section>
  );
}

/** Fixed bottom CTA - mobile only. */
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

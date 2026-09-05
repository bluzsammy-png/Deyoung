"use client";

import { useState } from "react";
import { ArrowRight, Clapperboard, Mic, Palette, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { go } from "./hash";
import { Reveal, TiltCard } from "./motion";

const PROOFS = [
  { icon: Sparkles, text: "One brief - a full 60-second script" },
  { icon: Palette, text: "5 visual styles in a single film" },
  { icon: Mic, text: "Shot, voiced, scored & captioned by the engine" },
];

/**
 * The 60-Second Campaign - the flagship proof section.
 * The real, shipped DeYoung film plays right on the page: not a promise, a result.
 */
export function CampaignStrip() {
  const [playing, setPlaying] = useState(false);

  return (
    <section id="campaign" aria-label="The 60-second campaign" className="py-16 md:py-24 bg-[var(--brand-black)] text-white relative overflow-hidden">
      <div className="absolute inset-0 dy-hero-grid opacity-40" aria-hidden />
      <div className="dy-orb absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-[#DC2626]/20" aria-hidden />

      <div className="relative mx-auto max-w-6xl px-4 grid lg:grid-cols-[1fr_1.1fr] gap-12 items-center dy-scene">
        {/* ---- copy ---- */}
        <Reveal>
          <p className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.3em] text-primary">
            <Clapperboard className="h-4 w-4" aria-hidden /> DeYoung Original - the 60-second campaign
          </p>
          <h2 className="mt-4 text-3xl md:text-5xl font-black tracking-tight uppercase leading-[1.02]">
            One brief in.<br />
            <span className="dy-grad-text">A whole film out.</span>
          </h2>
          <p className="mt-5 max-w-xl text-white/70 leading-relaxed">
            This film is the proof. One written brief - characters, script, scenes, voices, music and
            captions - planned, rendered and assembled by the DeYoung engine. Every voice you hear is a
            scripted line, every scene was a single instruction. The same engine that ships your videos.
          </p>

          <ul className="mt-7 space-y-3">
            {PROOFS.map(({ icon: Icon, text }, i) => (
              <li key={i} className="flex items-center gap-3 text-sm text-white/80">
                <span className="h-8 w-8 shrink-0 grid place-items-center border border-primary/60 bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" aria-hidden />
                </span>
                {text}
              </li>
            ))}
          </ul>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button
              onClick={() => go("#plans")}
              className="h-12 px-6 font-bold bg-primary hover:bg-[#B91C1C] text-white dy-glow-red"
            >
              Make your 60 seconds <ArrowRight className="h-4 w-4" aria-hidden />
            </Button>
            <Button
              onClick={() => go("#request")}
              variant="outline"
              className="h-12 px-6 font-bold border-white/30 bg-transparent text-white hover:bg-white hover:text-black"
            >
              Try the film planner
            </Button>
          </div>
        </Reveal>

        {/* ---- the film itself ---- */}
        <Reveal delay={120}>
          <TiltCard max={4} lift={6} className="p-[2px] bg-gradient-to-br from-[#DC2626] via-[#7F1D1D] to-[#DC2626] shadow-[0_0_60px_-15px_rgba(220,38,38,0.8)]">
            <div className="relative bg-black">
              <video
                className="w-full aspect-video object-contain bg-black"
                src="/video/deyoung-film-web.mp4?v=8"
                poster="/img/film-poster.jpg?v=8"
                controls
                preload="metadata"
                playsInline
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                aria-label="DeYoung 60-second campaign film"
              />
              <span
                className={`absolute top-3 left-3 inline-flex items-center gap-1.5 bg-black/70 backdrop-blur px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-white pointer-events-none transition-opacity ${playing ? "opacity-0" : "opacity-100"}`}
              >
                <span className="h-2 w-2 bg-primary rounded-full animate-pulse" aria-hidden />
                84s · sound on - characters talk
              </span>
              <span className="absolute bottom-3 right-3 bg-primary text-white px-2 py-1 text-[10px] font-black uppercase tracking-widest pointer-events-none">
                DeYoung Original
              </span>
            </div>
          </TiltCard>
          <p className="mt-3 text-center text-xs text-white/40 uppercase tracking-widest">
            The real film - no mockups, no borrowed footage
          </p>
        </Reveal>
      </div>
    </section>
  );
}

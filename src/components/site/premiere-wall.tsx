"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { Play, X, Star, Clock, ArrowRight } from "lucide-react";
import { Reveal } from "./motion";
import { Button } from "@/components/ui/button";
import { api, type Premiere } from "@/lib/types";
import { go } from "./hash";

/**
 * W2.2 — The Premiere Wall. The public showcase of finished DeYoung films.
 * Every entry is a real delivered render (published by the owner) or a manual
 * entry pointing at a public video. Cards hover-preview muted inline; the
 * lightbox plays the full film with sound. Honest by construction: the wall
 * only ever shows what /api/premieres publishes.
 */

const CATEGORIES = [
  { key: "all", label: "All premieres" },
  { key: "ai-film", label: "AI Film" },
  { key: "style-lab", label: "Style Lab" },
  { key: "studio", label: "Studio" },
  { key: "commercial", label: "Commercial" },
];

const CATEGORY_LABEL: Record<string, string> = {
  "ai-film": "AI Film",
  "style-lab": "Style Lab",
  studio: "Studio",
  commercial: "Commercial",
};

function fmtDuration(sec: number): string {
  if (!sec || sec <= 0) return "";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function PremiereWall() {
  const [premieres, setPremieres] = useState<Premiere[] | null>(null);
  const [filter, setFilter] = useState("all");
  const [active, setActive] = useState<Premiere | null>(null);
  const videoRefs = useRef(new Map<string, HTMLVideoElement>());

  useEffect(() => {
    api<{ premieres: Premiere[] }>("/api/premieres")
      .then((d) => setPremieres(d.premieres))
      .catch(() => setPremieres([]));
  }, []);

  // Close the lightbox with Escape like a real theater exit.
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setActive(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  const shown = useMemo(
    () =>
      premieres && filter !== "all"
        ? premieres.filter((p) => (p.category || "ai-film") === filter)
        : (premieres ?? []),
    [premieres, filter]
  );

  const hoverPlay = useCallback((id: string) => {
    const el = videoRefs.current.get(id);
    if (!el) return;
    el.play().catch(() => {
      /* hover preview is best-effort — the poster still shows */
    });
  }, []);

  const hoverStop = useCallback((id: string) => {
    const el = videoRefs.current.get(id);
    if (!el) return;
    el.pause();
    try {
      el.currentTime = 0;
    } catch {
      /* nothing playing yet */
    }
  }, []);

  return (
    <section id="premieres" className="scroll-mt-20 py-16 md:py-24 bg-[var(--brand-black)] text-white">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <p className="text-xs font-black uppercase tracking-[0.3em] text-primary">Now showing</p>
          <h2 className="mt-2 text-3xl font-black uppercase tracking-tight md:text-5xl">The Premiere Wall</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-white/60 md:text-base">
            Finished DeYoung films, the moment they leave the render fleet. Real deliveries — press play.
          </p>
        </div>

        {premieres && premieres.length > 0 && (
          <div className="mt-6 flex flex-wrap justify-center gap-2" role="tablist" aria-label="Premiere categories">
            {CATEGORIES.map((f) => {
              const count =
                f.key === "all"
                  ? premieres.length
                  : premieres.filter((p) => (p.category || "ai-film") === f.key).length;
              if (count === 0) return null;
              return (
                <button
                  key={f.key}
                  role="tab"
                  aria-selected={filter === f.key}
                  onClick={() => setFilter(f.key)}
                  className={`rounded-full border px-4 py-1.5 text-xs font-black uppercase tracking-widest transition-colors ${
                    filter === f.key
                      ? "border-primary bg-primary text-white"
                      : "border-white/20 text-white/60 hover:border-white/40 hover:text-white"
                  }`}
                >
                  {f.label} · {count}
                </button>
              );
            })}
          </div>
        )}

        {premieres === null ? (
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
            {[0, 1, 2].map((i) => (
              <div key={i} className="aspect-video animate-pulse rounded-xl bg-white/[0.04]" />
            ))}
          </div>
        ) : shown.length === 0 ? (
          <div className="mt-10 rounded-2xl border border-white/10 bg-white/[0.03] p-10 text-center">
            <p className="text-lg font-black uppercase tracking-widest text-white/80">The first premieres land here</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-white/50">
              The fleet is rolling. Delivered films premiere on this wall — subscribe and yours could be next.
            </p>
            <Button onClick={() => go("#subscribe")} className="mt-6 bg-primary font-bold text-white hover:bg-[#B91C1C]">
              Start your film <ArrowRight className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        ) : (
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((p, i) => (
              <Reveal key={p.id} delay={(i % 3) * 80}>
                <button
                  onClick={() => setActive(p)}
                  onMouseEnter={() => hoverPlay(p.id)}
                  onMouseLeave={() => hoverStop(p.id)}
                  className="group relative block w-full overflow-hidden rounded-xl border border-white/10 bg-neutral-900 text-left transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-primary hover:border-primary/50 hover:shadow-[0_16px_50px_-12px_rgba(220,38,38,0.55)]"
                  aria-label={`Play premiere: ${p.title}`}
                >
                  <div className="relative aspect-video w-full">
                    <video
                      ref={(el) => {
                        if (el) videoRefs.current.set(p.id, el);
                        else videoRefs.current.delete(p.id);
                      }}
                      src={p.videoSrc}
                      poster={p.posterUrl || undefined}
                      muted
                      loop
                      playsInline
                      preload="metadata"
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                    <span className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-black/30" aria-hidden />
                    <span className="absolute inset-0 flex items-center justify-center opacity-90 transition-opacity group-hover:opacity-0">
                      <span className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-white/80 bg-black/50 backdrop-blur-sm">
                        <Play className="ml-0.5 h-5 w-5 text-white" aria-hidden />
                      </span>
                    </span>
                    {p.featured && (
                      <span className="absolute top-2 left-2 flex items-center gap-1 bg-primary px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-white">
                        <Star className="h-3 w-3" aria-hidden /> Premiere
                      </span>
                    )}
                    <span className="absolute top-2 right-2 bg-black/85 px-2 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-white/90 backdrop-blur-sm">
                      {CATEGORY_LABEL[p.category] ?? p.category}
                    </span>
                    <span className="absolute bottom-2 left-2 right-2 flex items-end justify-between gap-2">
                      <span className="line-clamp-1 text-sm font-black uppercase tracking-wide text-white">{p.title}</span>
                      {p.durationSec > 0 && (
                        <span className="flex shrink-0 items-center gap-1 bg-black/70 px-1.5 py-0.5 text-[10px] font-black text-white/80">
                          <Clock className="h-3 w-3" aria-hidden /> {fmtDuration(p.durationSec)}
                        </span>
                      )}
                    </span>
                  </div>
                </button>
              </Reveal>
            ))}
          </div>
        )}
      </div>

      {active && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/95 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={`Premiere: ${active.title}`}
          onClick={() => setActive(null)}
        >
          <button
            className="absolute top-4 right-4 bg-white/10 p-2 text-white hover:bg-primary"
            aria-label="Close premiere"
            onClick={() => setActive(null)}
          >
            <X className="h-6 w-6" />
          </button>
          <figure className="relative w-full max-w-4xl" onClick={(e) => e.stopPropagation()}>
            <div className="relative aspect-video w-full bg-neutral-950">
              <video
                key={active.id}
                src={active.videoSrc}
                poster={active.posterUrl || undefined}
                controls
                autoPlay
                playsInline
                className="absolute inset-0 h-full w-full"
              />
            </div>
            <figcaption className="mt-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="border-l-2 border-primary pl-2 text-lg font-black uppercase tracking-wide">{active.title}</span>
                <span className="bg-white/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-white/70">
                  {CATEGORY_LABEL[active.category] ?? active.category}
                </span>
                {active.durationSec > 0 && (
                  <span className="flex items-center gap-1 text-[11px] font-bold text-white/50">
                    <Clock className="h-3 w-3" aria-hidden /> {fmtDuration(active.durationSec)}
                  </span>
                )}
              </div>
              {active.logline && <p className="mt-2 text-sm leading-relaxed text-white/60">{active.logline}</p>}
              <div className="mt-3 flex items-center justify-between gap-3">
                <p className="text-[11px] uppercase tracking-widest text-white/35">
                  Premiered {new Date(active.postedAt).toLocaleDateString()}
                </p>
                <Button size="sm" onClick={() => go("#subscribe")} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
                  Make one like this <ArrowRight className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            </figcaption>
          </figure>
        </div>
      )}
    </section>
  );
}

/** Poster image used inside the admin Premieres tab (safe for remote URLs). */
export function PremierePoster({ src, alt }: { src: string; alt: string }) {
  if (!src) return null;
  return <Image unoptimized src={src} alt={alt} width={96} height={54} className="rounded border border-white/10 object-cover" />;
}

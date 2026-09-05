"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ChevronLeft, ChevronRight, Clapperboard, Pause, Play } from "lucide-react";

/**
 * ShowReel - the hero slideshow that replaced the static "DY" portrait card.
 * Mixed media: character art (5 styles), real-style photo, animated GIF,
 * muted film loops and a pure-CSS banner - auto-rotating with captions.
 */

type Slide = {
  kind: "image" | "gif" | "video" | "design";
  src?: string;
  tag: string;
  title: string;
  sub: string;
  alt?: string;
  /** seconds this slide stays on screen */
  secs: number;
};

const SLIDES: Slide[] = [
  {
    kind: "image",
    src: "/showreel/style-lineup.png",
    tag: "Every style",
    title: "Five worlds. One prompt.",
    sub: "Cartoon · Stick man · Real · Anime · Kids",
    alt: "Five DeYoung character styles lined up on a red stage",
    secs: 5,
  },
  {
    kind: "video",
    src: "/showreel/clip-cartoon.mp4",
    tag: "Cartoon",
    title: "One sentence in. A film out.",
    sub: "3D cartoon - generated start to finish",
    alt: "Cartoon boy typing a prompt as his film renders",
    secs: 5.5,
  },
  {
    kind: "image",
    src: "/showreel/style-stickman.png",
    tag: "Stick man",
    title: "Sign up ten seconds, three ways.",
    sub: "Google · Apple · email - pick a door",
    alt: "Stick man running toward three glowing sign-up doors",
    secs: 4.5,
  },
  {
    kind: "gif",
    src: "/showreel/stickman-run.gif",
    tag: "Animated GIF",
    title: "Every frame in motion.",
    sub: "Stick-man magic, hand-drawn frame by frame",
    alt: "Stick man with a red camera-eye running in a loop",
    secs: 4,
  },
  {
    kind: "image",
    src: "/showreel/style-anime.png",
    tag: "Anime",
    title: "Watch it build - scene by scene.",
    sub: "Your dashboard while the AI directs",
    alt: "Anime director surrounded by floating production screens",
    secs: 4.5,
  },
  {
    kind: "video",
    src: "/showreel/clip-doors.mp4",
    tag: "Real footage",
    title: "Three doors. One click.",
    sub: "The sign-up scene from the 60-second film",
    alt: "Stick man leaping through a glowing sign-up door",
    secs: 5,
  },
  {
    kind: "image",
    src: "/showreel/style-real.png",
    tag: "Ultra realistic",
    title: "Straight to your feed.",
    sub: "Cinema-grade realism, zero editing",
    alt: "Woman on a sofa at sunset watching a video on her phone",
    secs: 4.5,
  },
  {
    kind: "image",
    src: "/showreel/style-split.png",
    tag: "Split screen",
    title: "Anime ⇄ real. Your call.",
    sub: "Same prompt, two worlds - blend or switch",
    alt: "Anime girl and real actor back to back under studio lights",
    secs: 4.5,
  },
  {
    kind: "design",
    tag: "Showreel",
    title: "Your prompt. Our five styles.",
    sub: "Pick a world - or blend them all",
    secs: 4.5,
  },
  {
    kind: "image",
    src: "/showreel/style-kids.png",
    tag: "Kids cartoon",
    title: "My movie arrived. Ready to post.",
    sub: "Even the robot ships same-day",
    alt: "Children's cartoon robot holding a gift box with a red bow",
    secs: 4.5,
  },
];

function subscribeReducedMotion(cb: () => void) {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

export function ShowReel() {
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduced = useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false
  );
  const touchX = useRef<number | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const slide = SLIDES[idx];

  const next = useCallback(() => setIdx((i) => (i + 1) % SLIDES.length), []);
  const prev = useCallback(
    () => setIdx((i) => (i - 1 + SLIDES.length) % SLIDES.length),
    []
  );

  /* autoplay - per-slide duration, pause on hover/touch/hidden tab/reduced motion */
  useEffect(() => {
    if (paused || reduced || document.hidden) return;
    const t = setTimeout(next, slide.secs * 1000);
    const onVis = () => document.hidden && setPaused(false); // timer re-arms on return
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearTimeout(t);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [idx, paused, reduced, next, slide.secs]);

  /* drive the active video slide; pause it when hovering */
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    if (paused || (document.hidden && !reduced)) v.pause();
    else v.play().catch(() => {});
  }, [idx, paused, reduced]);

  const onTouchStart = (e: React.TouchEvent) => {
    touchX.current = e.touches[0].clientX;
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    if (Math.abs(dx) > 40) (dx < 0 ? next : prev)();
    touchX.current = null;
  };

  return (
    <section
      aria-roledescription="carousel"
      aria-label="DeYoung style showreel"
      className="relative select-none"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {/* frame */}
      <div className="relative aspect-square overflow-hidden bg-neutral-950 touch-pan-y">
        {/* stacked slides */}
        {SLIDES.map((s, i) => {
          const active = i === idx;
          return (
            <div
              key={i}
              aria-hidden={!active}
              className={`absolute inset-0 transition-all duration-700 ease-out ${
                active ? "opacity-100 scale-100 z-10" : "opacity-0 scale-[1.06] z-0"
              }`}
            >
              {s.kind === "design" ? (
                <DesignBanner />
              ) : s.kind === "video" ? (
                active ? (
                  <video
                    ref={videoRef}
                    src={s.src}
                    muted
                    loop
                    playsInline
                    autoPlay={!reduced}
                    preload="auto"
                    className="h-full w-full object-cover"
                    aria-label={s.alt || s.title}
                  />
                ) : (
                  <div className="h-full w-full bg-neutral-900" />
                )
              ) : s.kind === "gif" ? (
                <img
                  src={s.src}
                  alt={active ? s.alt || s.title : ""}
                  className={`h-full w-full object-cover white-bg ${
                    active && !reduced ? "dy-kenburns" : ""
                  }`}
                  loading="lazy"
                />
              ) : (
                <div className={`relative h-full w-full ${active && !reduced ? "dy-kenburns" : ""}`}>
                  <Image
                    src={s.src!}
                    alt={active ? s.alt || s.title : ""}
                    fill
                    sizes="(max-width: 768px) 80vw, 33vw"
                    className="object-cover"
                    priority={i === 0}
                  />
                </div>
              )}
            </div>
          );
        })}

        {/* caption (write-up) */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/90 via-black/55 to-transparent pt-14 pb-7 px-4">
          <p className="inline-flex items-center gap-1.5 bg-primary px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-white">
            <Clapperboard className="h-3 w-3" aria-hidden />
            {slide.tag}
          </p>
          <p className="mt-2 text-lg font-black leading-tight text-white">{slide.title}</p>
          <p className="mt-0.5 text-xs text-white/65">{slide.sub}</p>
        </div>

        {/* top row: live chip + counter + controls */}
        <div className="absolute top-0 inset-x-0 z-20 flex items-center justify-between px-3 pt-3">
          <span className="dy-glass inline-flex items-center gap-1.5 px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.2em] text-white/85">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" aria-hidden />
            Showreel
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={prev}
              aria-label="Previous slide"
              className="dy-glass flex h-8 w-8 items-center justify-center rounded-full text-white/90 hover:bg-primary transition-colors"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </button>
            <button
              onClick={() => setPaused((p) => !p)}
              aria-label={paused ? "Play slideshow" : "Pause slideshow"}
              className="dy-glass flex h-8 w-8 items-center justify-center rounded-full text-white/90 hover:bg-primary transition-colors"
            >
              {paused ? <Play className="h-3.5 w-3.5" aria-hidden /> : <Pause className="h-3.5 w-3.5" aria-hidden />}
            </button>
            <button
              onClick={next}
              aria-label="Next slide"
              className="dy-glass flex h-8 w-8 items-center justify-center rounded-full text-white/90 hover:bg-primary transition-colors"
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>

        {/* progress + dots */}
        <div className="absolute inset-x-0 bottom-0 z-30 h-[3px] bg-white/10">
          <div
            key={`${idx}-${paused}`}
            className="h-full bg-primary"
            style={{
              animation: reduced
                ? undefined
                : `dy-progress ${slide.secs}s linear forwards`,
              animationPlayState: paused ? "paused" : "running",
              width: reduced ? "100%" : undefined,
            }}
          />
        </div>
        <div className="absolute bottom-2 right-3 z-20 flex items-center gap-1.5">
          {SLIDES.map((_, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              aria-label={`Go to slide ${i + 1}`}
              aria-current={i === idx}
              className={`h-1.5 rounded-full transition-all ${
                i === idx ? "w-5 bg-primary" : "w-1.5 bg-white/40 hover:bg-white/70"
              }`}
            />
          ))}
        </div>
      </div>

      {/* counter */}
      <span className="dy-glass absolute -top-3 left-3 z-30 rounded-md px-2 py-0.5 text-[10px] font-black tracking-widest text-white/85">
        {String(idx + 1).padStart(2, "0")}/{String(SLIDES.length).padStart(2, "0")}
      </span>
    </section>
  );
}

/** Pure-CSS red/black film-strip banner slide. */
function DesignBanner() {
  return (
    <div className="relative flex h-full w-full flex-col justify-center overflow-hidden bg-[#0A0A0A] px-6">
      {/* sprocket strips */}
      <div className="absolute top-0 inset-x-0 flex justify-between px-2 py-2" aria-hidden>
        {Array.from({ length: 9 }).map((_, i) => (
          <span key={i} className="h-3 w-4 rounded-[2px] bg-white/15" />
        ))}
      </div>
      <div className="absolute bottom-0 inset-x-0 flex justify-between px-2 py-2" aria-hidden>
        {Array.from({ length: 9 }).map((_, i) => (
          <span key={i} className="h-3 w-4 rounded-[2px] bg-white/15" />
        ))}
      </div>
      <div
        className="absolute -right-10 -top-10 h-44 w-44 rounded-full bg-primary/25 blur-2xl"
        aria-hidden
      />
      <div
        className="absolute -left-12 -bottom-12 h-52 w-52 rounded-full bg-[#7F1D1D]/30 blur-2xl"
        aria-hidden
      />
      <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/50">
        DeYoung prompt booth
      </p>
      <p className="mt-3 text-3xl font-black leading-[1.02] tracking-tight text-white uppercase">
        Same prompt.
        <br />
        <span className="dy-grad-text">Every style</span>
        <br />
        you can imagine.
      </p>
      <p className="mt-3 text-xs text-white/60">
        Cartoon · Stick man · Ultra real · Anime · Kids
      </p>
    </div>
  );
}

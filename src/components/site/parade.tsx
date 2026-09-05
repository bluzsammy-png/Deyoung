"use client";

import type { CSSProperties } from "react";

type Runner = {
  sprite: string;
  w: number; // display px (square)
  dur: number; // seconds to cross the screen
  delay: number; // negative = already mid-run on load
  bottom: number;
};

const CAST_A: Runner[] = [
  { sprite: "/parade/runner.png", w: 78, dur: 15, delay: 0, bottom: 18 },
  { sprite: "/parade/dog.png", w: 84, dur: 11.5, delay: -4, bottom: 22 },
  { sprite: "/parade/girl.png", w: 72, dur: 16.5, delay: -9, bottom: 18 },
  { sprite: "/parade/hopper.png", w: 62, dur: 21, delay: -13, bottom: 20 },
  { sprite: "/parade/kid.png", w: 68, dur: 18.5, delay: -6, bottom: 20 },
];

const CAST_B: Runner[] = [
  { sprite: "/parade/kid.png", w: 66, dur: 17, delay: -2, bottom: 20 },
  { sprite: "/parade/girl.png", w: 74, dur: 15, delay: -7, bottom: 18 },
  { sprite: "/parade/hopper.png", w: 64, dur: 22, delay: -11, bottom: 20 },
  { sprite: "/parade/runner.png", w: 80, dur: 13.5, delay: -5, bottom: 18 },
  { sprite: "/parade/dog.png", w: 78, dur: 12, delay: -15, bottom: 22 },
];

/**
 * Cartoon parade - DeYoung's stick-character cast runs across a branded strip.
 * Pure CSS sprite-sheet animation; hidden from screen readers; reduced-motion safe.
 */
export function Parade({ variant = "a", className = "" }: { variant?: "a" | "b"; className?: string }) {
  const cast = variant === "a" ? CAST_A : CAST_B;
  return (
    <div
      className={`dy-parade relative overflow-hidden bg-[var(--brand-black)] ${className}`}
      aria-hidden
    >
      <div className="dy-parade-track" />
      <span className="dy-parade-sign">DEYOUNG PARK</span>
      {cast.map((r, i) => (
        <div
          key={i}
          className="dy-parader"
          style={
            {
              "--pd": `${r.dur}s`,
              "--pdelay": `${r.delay}s`,
              "--pb": `${r.bottom}px`,
              "--pw": `${r.w}px`,
              "--sx": `${6 + i * 21}%`,
            } as CSSProperties
          }
        >
          <span className="dy-sprite" style={{ backgroundImage: `url(${r.sprite})` }} />
        </div>
      ))}
    </div>
  );
}

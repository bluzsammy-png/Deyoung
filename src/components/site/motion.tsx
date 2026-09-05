"use client";

import { useEffect, useRef, type ReactNode, type CSSProperties } from "react";

const finePointer = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
  !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * TiltCard - pointer-reactive 3D tilt with a moving glare highlight.
 * Automatically disabled on touch devices and for reduced-motion users.
 */
export function TiltCard({
  children,
  className = "",
  max = 7,
  lift = 6,
  style,
}: {
  children: ReactNode;
  className?: string;
  /** Max rotation in degrees. */
  max?: number;
  /** TranslateZ lift in px at full tilt. */
  lift?: number;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const frame = useRef(0);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  function onMove(e: React.PointerEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el || !finePointer()) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      const target = ref.current;
      if (!target) return;
      target.style.transform = `perspective(950px) rotateX(${(-py * max).toFixed(2)}deg) rotateY(${(px * max).toFixed(2)}deg) translateZ(${lift}px)`;
      const glare = target.querySelector<HTMLElement>(".dy-glare");
      if (glare) {
        glare.style.opacity = "1";
        glare.style.background = `radial-gradient(460px circle at ${((px + 0.5) * 100).toFixed(1)}% ${((py + 0.5) * 100).toFixed(1)}%, rgba(255,255,255,0.16), transparent 46%)`;
      }
    });
  }

  function onLeave() {
    cancelAnimationFrame(frame.current);
    const el = ref.current;
    if (!el) return;
    el.style.transform = "";
    const glare = el.querySelector<HTMLElement>(".dy-glare");
    if (glare) glare.style.opacity = "0";
  }

  return (
    <div
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      className={`dy-tilt ${className}`}
      style={{ transition: "transform 0.3s cubic-bezier(0.2, 0.6, 0.2, 1)", ...style }}
    >
      {children}
      <div className="dy-glare" style={{ opacity: 0 }} aria-hidden />
    </div>
  );
}

/**
 * Reveal - fades/slides children in the first time they enter the viewport.
 */
export function Reveal({
  children,
  className = "",
  delay = 0,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  /** Stagger delay in ms. */
  delay?: number;
  as?: "div" | "section" | "li" | "article";
}) {
  const ref = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!finePointer()) {
      el.classList.add("dy-in");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.classList.add("dy-in");
            io.disconnect();
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as any}
      className={`dy-reveal ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

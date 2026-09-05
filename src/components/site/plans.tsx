"use client";

import { ArrowLeft, Check, Clapperboard, Flame, Timer, X, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { money, type Plan, type PlanFeature } from "@/lib/types";
import { go } from "./hash";
import { SectionHead } from "./sections";
import { TiltCard, Reveal } from "./motion";

function planFeatures(plan: Plan): PlanFeature[] {
  try {
    const parsed = JSON.parse(plan.featuresJson);
    return Array.isArray(parsed) ? (parsed as PlanFeature[]) : [];
  } catch {
    return [];
  }
}

function slashedPrice(price: number, compareAt?: number | null): { was: number; save: number } | null {
  if (!compareAt || compareAt <= price) return null;
  return { was: compareAt, save: Math.round(((compareAt - price) / compareAt) * 100) };
}

/**
 * Public pricing section - Beginner / Pro / Elite.
 * The 60-second hook is the headline; every number comes from the owner-editable plans.
 */
export function PlansSection({
  plans,
  currency,
  standalone = false,
}: {
  plans: Plan[];
  currency: string;
  /** When true this section is the whole #plans page (own route), not a home-page band. */
  standalone?: boolean;
}) {
  if (plans.length === 0) return null;

  return (
    <section
      id="plans"
      aria-label="Video subscription plans"
      className={`${standalone ? "pt-12 pb-16 md:pt-16 md:pb-24" : "py-16 md:py-24"} bg-[var(--brand-black)] text-white`}
    >
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <p className="text-xs font-black uppercase tracking-[0.3em] text-primary">AI Video Studio</p>
          <h2 className="mt-3 text-3xl md:text-5xl font-black tracking-tight uppercase">
            60 seconds. One pass.<br className="hidden md:block" /> Where others stop at 15.
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-neutral-300 leading-relaxed">
            Subscribe monthly, submit your prompt, and DeYoung&apos;s engine renders it -
            up to a full minute in a single generation. Pick the tier that fits how much you ship.
          </p>
        </div>

        {/* urgency banner - the founding window is closed, rates rose */}
        <div className="mt-8 border-2 border-primary/70 bg-primary/10 px-4 py-3.5 flex flex-col sm:flex-row items-center justify-center gap-x-4 gap-y-1.5 text-center">
          <span className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-widest text-white">
            <Flame className="h-4 w-4 text-primary" aria-hidden />
            Prices just went up
          </span>
          <span className="text-sm text-neutral-300">
            The founding window is closed - the rates below are the new rate card, and the
            next rise is already scheduled. <strong className="text-white">Lock yours in now</strong> -
            your rate stays locked while you stay subscribed.
          </span>
        </div>

        <div className="mt-12 grid md:grid-cols-3 gap-5 items-stretch dy-scene">
          {plans.map((plan, i) => {
            const popular = plan.code === "pro";
            const slash = slashedPrice(plan.priceMonthly, plan.compareAtPrice);
            return (
              <Reveal key={plan.id} delay={i * 110}>
              <TiltCard
                max={6}
                lift={8}
                className={`h-full ${popular ? "p-[2px] bg-gradient-to-b from-[#DC2626] via-[#7F1D1D] to-[#DC2626] shadow-[0_0_50px_-12px_rgba(220,38,38,0.7)]" : ""}`}
              >
              <div
                className={`relative flex flex-col p-6 h-full border-2 ${
                  popular
                    ? "border-primary bg-white text-neutral-900"
                    : "border-white/15 bg-white/5 text-white"
                }`}
              >
                {popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-[11px] font-black uppercase tracking-widest px-3 py-1">
                    Most popular
                  </span>
                )}
                <h3 className="text-xl font-black uppercase tracking-tight">{plan.name}</h3>
                <p className={`mt-1 text-sm ${popular ? "text-neutral-600" : "text-neutral-400"}`}>{plan.blurb}</p>
                {slash && (
                  <p className="mt-3 flex items-center gap-2">
                    <span className={`text-base font-bold line-through ${popular ? "text-neutral-400" : "text-neutral-500"}`}>
                      {money(slash.was, plan.currency || currency)}
                    </span>
                    <span className="bg-primary text-white text-[10px] font-black uppercase tracking-widest px-2 py-0.5">
                      Save {slash.save}%
                    </span>
                  </p>
                )}
                <p className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-black tracking-tight">
                    {money(plan.priceMonthly, plan.currency || currency)}
                  </span>
                  <span className={`text-sm font-semibold ${popular ? "text-neutral-500" : "text-neutral-400"}`}>/month</span>
                </p>
                <p className={`mt-1 text-[11px] font-semibold uppercase tracking-widest ${popular ? "text-primary" : "text-primary"}`}>
                  New rate - rises again soon
                </p>
                <ul className="mt-5 space-y-2.5 text-sm flex-1">
                  {planFeatures(plan).map((f) => (
                    <li key={f.label} className="flex items-start gap-2">
                      {f.included ? (
                        <Check className="h-4 w-4 mt-0.5 shrink-0 text-primary" aria-hidden />
                      ) : (
                        <X className={`h-4 w-4 mt-0.5 shrink-0 ${popular ? "text-neutral-300" : "text-neutral-600"}`} aria-hidden />
                      )}
                      <span className={f.included ? "" : popular ? "text-neutral-400 line-through" : "text-neutral-500 line-through"}>
                        {f.label}
                      </span>
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => go(`#subscribe?plan=${plan.code}`)}
                  className={`mt-6 w-full h-11 font-bold ${
                    popular
                      ? "bg-primary hover:bg-[#B91C1C] text-white"
                      : "bg-white text-[var(--brand-black)] hover:bg-primary hover:text-white"
                  }`}
                >
                  <Zap className="h-4 w-4" aria-hidden /> Subscribe to {plan.name}
                </Button>
                <p className={`mt-2 text-center text-[11px] ${popular ? "text-neutral-500" : "text-neutral-500"}`}>
                  Your rate stays locked for as long as you keep the subscription - even after prices rise.
                </p>
              </div>
              </TiltCard>
              </Reveal>
            );
          })}
        </div>

        <div className="mt-10 grid sm:grid-cols-3 gap-3 text-sm">
          <div className="border border-white/15 p-4 flex items-start gap-3">
            <Timer className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden />
            <p className="text-neutral-300">
              <strong className="text-white">Queue-first:</strong> you get a live queue position and an honest ETA - never a broken promise.
            </p>
          </div>
          <div className="border border-white/15 p-4 flex items-start gap-3">
            <Clapperboard className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden />
            <p className="text-neutral-300">
              <strong className="text-white">Same prompt, different lengths:</strong> Beginner 15s clips, Pro &amp; Elite the full 60s pass.
            </p>
          </div>
          <div className="border border-white/15 p-4 flex items-start gap-3">
            <Zap className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden />
            <p className="text-neutral-300">
              <strong className="text-white">Already rendered?</strong> Identical requests deliver instantly from the cache - no waiting.
            </p>
          </div>
        </div>

        <p className="mt-8 text-center">
          <button
            onClick={() => go("#request")}
            className="text-sm font-bold text-primary hover:underline underline-offset-4"
          >
            Already subscribed? Submit your video request <ArrowRight className="h-4 w-4 inline align-[-2px]" aria-hidden />
          </button>
        </p>
        {standalone && (
          <p className="mt-4 text-center">
            <button
              onClick={() => go("#")}
              className="text-sm font-bold text-white/50 hover:text-white hover:underline underline-offset-4"
            >
              <ArrowLeft className="h-4 w-4 inline align-[-2px]" aria-hidden /> Back to the homepage
            </button>
          </p>
        )}
      </div>
    </section>
  );
}

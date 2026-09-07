"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/types";
import { go } from "@/components/site/hash";
import { useSessionBadge } from "@/components/site/use-session";
import {
  Activity,
  Clapperboard,
  Film,
  Gauge,
  Infinity as InfinityIcon,
  Loader2,
  Plus,
  Sparkles,
} from "lucide-react";

type Me = {
  blocked?: { status: string; reason: string };
  user?: { id: string; email: string; name: string; image: string; role: string };
  unlimited?: boolean;
  subscription: { id: string; planCode: string; status: string; periodEnd: string | null } | null;
  plan: {
    code: string;
    name: string;
    maxVideosMonth: number;
    maxSecondsVideo: number;
    maxResolution: string;
    watermark: boolean;
    concurrentJobs: number;
    queuePriority: number;
    commercial: boolean;
    audio: boolean;
  } | null;
  usage: {
    videosUsed: number;
    videosQuota: number | null;
    gpuMinutesUsed: number;
    gpuMinutesBudget: number | null;
    resetAt: string | null;
  };
  requests: {
    id: string;
    prompt: string;
    seconds: number;
    resolution: string;
    status: string;
    resultUrl: string;
    gpuMinutes: number;
    createdAt: string;
  }[];
  projects: { id: string; title: string; niche: string; status: string; updatedAt: string }[];
};

const STATUS_STYLE: Record<string, string> = {
  queued: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  rendering: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  done: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  cancelled: "bg-white/10 text-white/50 border-white/20",
};

/* Animated GPU-life ring — the film-simulator centerpiece. */
function GpuRing({
  used,
  budget,
  unlimited,
}: {
  used: number;
  budget: number | null;
  unlimited: boolean;
}) {
  const pct = unlimited ? 100 : budget && budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 0;
  const R = 52;
  const C = 2 * Math.PI * R;
  const [anim, setAnim] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setAnim(pct), 150);
    return () => clearTimeout(t);
  }, [pct]);

  return (
    <div className="relative h-40 w-40 shrink-0">
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90">
        <circle cx="64" cy="64" r={R} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
        <circle
          cx="64"
          cy="64"
          r={R}
          fill="none"
          stroke="url(#gpuGrad)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C - (C * anim) / 100}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
        <defs>
          <linearGradient id="gpuGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#DC2626" />
            <stop offset="100%" stopColor="#F87171" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {unlimited ? (
          <>
            <InfinityIcon className="h-8 w-8 text-primary" aria-hidden />
            <span className="mt-1 text-[11px] font-black uppercase tracking-widest text-white/60">unlimited</span>
          </>
        ) : (
          <>
            <span className="text-2xl font-black tabular-nums">{budget === null ? "—" : budget - used}</span>
            <span className="text-[11px] font-black uppercase tracking-widest text-white/60">GPU min left</span>
          </>
        )}
      </div>
    </div>
  );
}

export function DashboardView() {
  const [me, setMe] = useState<Me | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const badge = useSessionBadge();

  const load = useCallback(() => {
    api<Me>("/api/me")
      .then(setMe)
      .catch((e) => setErr(e instanceof Error ? e.message : "Could not load dashboard"));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000); // live like a film simulator
    return () => clearInterval(t);
  }, [load]);

  if (err) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] px-4 py-24 text-center text-white">
        <p className="text-lg font-bold">{err}</p>
        <Button onClick={() => go("/signin")} className="mt-6 bg-primary font-bold text-white hover:bg-[#B91C1C]">
          Sign in
        </Button>
      </div>
    );
  }
  if (!me) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[var(--brand-black)] text-white">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-label="Loading dashboard" />
      </div>
    );
  }
  if (me.blocked) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] px-4 py-24 text-center text-white">
        <p className="text-3xl font-black uppercase text-primary">Account {me.blocked.status}</p>
        <p className="mt-3 text-white/60">{me.blocked.reason || "Contact support."}</p>
      </div>
    );
  }

  const u = me.usage;
  const firstName = (me.user?.name || me.user?.email || "").split(" ")[0] || "there";

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] pb-20 text-white">
      <div className="mx-auto max-w-6xl px-4 py-10 md:py-14">
        {/* header row */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.25em] text-primary">Your studio</p>
            <h1 className="mt-1 text-3xl font-black uppercase md:text-4xl">
              {me.unlimited ? "Owner console" : `Welcome back, ${firstName}`}
            </h1>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => go("/studio")} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
              <Clapperboard className="h-4 w-4" aria-hidden /> Open AI Film Studio
            </Button>
            {badge?.admin && (
              <Button onClick={() => go("/admin")} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                Admin panel
              </Button>
            )}
          </div>
        </div>

        {/* top cards */}
        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {/* GPU life */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-widest text-white/50">
              <Gauge className="h-4 w-4 text-primary" aria-hidden /> GPU life
            </div>
            <div className="mt-4 flex items-center gap-5">
              <GpuRing used={u.gpuMinutesUsed} budget={u.gpuMinutesBudget} unlimited={Boolean(me.unlimited)} />
              <div className="space-y-2 text-sm">
                <p className="text-white/60">
                  <span className="font-black text-white">{u.gpuMinutesUsed}</span> GPU min burned this cycle
                </p>
                {u.gpuMinutesBudget !== null && (
                  <p className="text-white/60">
                    Plan budget: <span className="font-black text-white">{u.gpuMinutesBudget}</span> min
                  </p>
                )}
                {u.resetAt && (
                  <p className="text-white/40">
                    Resets {new Date(u.resetAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </p>
                )}
                <p className="flex items-center gap-1 text-white/40">
                  <Activity className="h-3 w-3" aria-hidden /> live · refreshes every 15s
                </p>
              </div>
            </div>
          </div>

          {/* render credits */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-widest text-white/50">
              <Film className="h-4 w-4 text-primary" aria-hidden /> Render credits
            </div>
            {me.unlimited ? (
              <div className="mt-6">
                <p className="text-4xl font-black text-primary">∞</p>
                <p className="mt-2 text-sm text-white/60">Owner account — every studio feature, no quota, no watermark.</p>
              </div>
            ) : (
              <div className="mt-6">
                <p className="text-4xl font-black">
                  {u.videosUsed}
                  <span className="text-white/30">/{u.videosQuota ?? "—"}</span>
                </p>
                {(() => {
                  const pct = u.videosQuota ? Math.min(100, (u.videosUsed / u.videosQuota) * 100) : 0;
                  return (
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
                      <div className="h-full rounded-full bg-primary transition-all duration-700" style={{ width: `${pct}%` }} />
                    </div>
                  );
                })()}
                <p className="mt-3 text-sm text-white/60">
                  {me.plan
                    ? `${me.plan.name} · up to ${me.plan.maxSecondsVideo}s · ${me.plan.maxResolution}${me.plan.watermark ? " · watermarked" : " · no watermark"}`
                    : "No active plan yet."}
                </p>
              </div>
            )}
          </div>

          {/* subscription */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-widest text-white/50">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden /> Subscription
            </div>
            {me.unlimited ? (
              <div className="mt-6">
                <p className="text-xl font-black uppercase">Owner — free</p>
                <p className="mt-2 text-sm text-white/60">You run this studio. Everything is unlocked.</p>
              </div>
            ) : me.subscription && me.plan ? (
              <div className="mt-6">
                <p className="text-xl font-black uppercase">{me.plan.name}</p>
                <p className="mt-1 text-sm capitalize text-emerald-400">● {me.subscription.status}</p>
                {me.subscription.periodEnd && (
                  <p className="mt-2 text-sm text-white/50">
                    Renews {new Date(me.subscription.periodEnd).toLocaleDateString()}
                  </p>
                )}
                <Button onClick={() => go("/subscribe")} size="sm" variant="outline" className="mt-4 border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                  Change plan
                </Button>
              </div>
            ) : (
              <div className="mt-6">
                <p className="text-xl font-black uppercase text-white/80">No plan yet</p>
                <p className="mt-2 text-sm text-white/60">Pick a plan to unlock the render queue — takes two minutes.</p>
                <Button onClick={() => go("/subscribe")} size="sm" className="mt-4 bg-primary font-bold text-white hover:bg-[#B91C1C]">
                  Choose a plan
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* renders + projects */}
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-black uppercase tracking-widest text-white/50">Recent renders</h2>
              <Button size="sm" onClick={() => go("/studio")} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
                <Plus className="h-4 w-4" aria-hidden /> New film
              </Button>
            </div>
            <div className="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1 [scrollbar-width:thin]">
              {me.requests.length === 0 && <p className="text-sm text-white/40">No renders yet — your first film is one prompt away.</p>}
              {me.requests.map((r) => (
                <div key={r.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="line-clamp-2 text-sm text-white/80">{r.prompt}</p>
                    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-black uppercase ${STATUS_STYLE[r.status] ?? STATUS_STYLE.cancelled}`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-white/40">
                    {r.seconds}s · {r.resolution} · {r.gpuMinutes} GPU min · {new Date(r.createdAt).toLocaleString()}
                  </p>
                  {r.status === "done" && r.resultUrl && (
                    <a href={r.resultUrl} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs font-bold text-primary hover:underline">
                      Watch your film →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <h2 className="text-sm font-black uppercase tracking-widest text-white/50">Studio projects</h2>
            <div className="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1 [scrollbar-width:thin]">
              {me.projects.length === 0 && (
                <p className="text-sm text-white/40">
                  Nothing in development. Open the studio and let the agent write your first script.
                </p>
              )}
              {me.projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => go(`/studio?p=${p.id}`)}
                  className="w-full rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left transition-colors hover:border-primary/40"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-bold">{p.title}</p>
                    <span className="rounded-full border border-white/15 px-2 py-0.5 text-[11px] font-black uppercase text-white/60">
                      {p.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-white/40">
                    {p.niche || "custom"} · updated {new Date(p.updatedAt).toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

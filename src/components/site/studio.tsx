"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  ArrowRight, BadgeCheck, CircleDot, Clock, Cpu, Film, Gauge, ListVideo, Loader2, Lock,
  Play, RadioTower, Send, Upload, UserCircle2, Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type HomeData, type StudioOverview, type StudioRequest, type StudioUser } from "@/lib/types";
import { AuthView } from "./auth-view";
import { SubscribeView } from "./subscribe-view";
import { EmptyState, ProfileTab, SupportTab, VideosTab } from "./studio-tabs";
import { VoiceClonePanel, useLicensedVoices } from "./voice-clone";
import { LogoMark } from "./logo";
import { go } from "./hash";

type Tab = "create" | "queue" | "videos" | "profile" | "support";

const TABS: { key: Tab; label: string; icon: typeof Film }[] = [
  { key: "create", label: "Create", icon: Film },
  { key: "queue", label: "Queue", icon: ListVideo },
  { key: "videos", label: "My Videos", icon: Play },
  { key: "profile", label: "Profile", icon: UserCircle2 },
  { key: "support", label: "Support", icon: RadioTower },
];

const VOICES = [
  { code: "", label: "No voice - silent cut" },
  { code: "amara", label: "Amara - warm female" },
  { code: "kossi", label: "Kossi - bright male" },
  { code: "zola", label: "Zola - confident female" },
  { code: "dee", label: "Dee - deep male narrator" },
  { code: "narrator", label: "Narrator - documentary" },
];

type MeQuota = {
  user: StudioUser;
  subscription: { id: string; planCode: string; status: string; periodEnd: string } | null;
  plan: { code: string; name: string } | null;
  used: number;
};

export function StudioView() {
  const [user, setUser] = useState<StudioUser | null>(null);
  const [hasPlan, setHasPlan] = useState(false);
  const [checking, setChecking] = useState(true);
  const [gateKey, setGateKey] = useState(0);
  const [tab, setTab] = useState<Tab>("create");

  useEffect(() => {
    let alive = true;
    api<MeQuota>("/api/user/me")
      .then((r) => {
        if (!alive) return;
        setUser(r.user);
        // The server only returns a subscription when it is ACTIVE and unexpired.
        setHasPlan(Boolean(r.subscription));
        setChecking(false);
      })
      .catch(() => {
        if (!alive) return;
        setUser(null);
        setChecking(false);
      });
    return () => {
      alive = false;
    };
  }, [gateKey]);

  if (checking) {
    return (
      <main className="flex-1 bg-[var(--brand-black)] text-white min-h-[70vh] grid place-items-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex-1">
        <AuthView onAuthed={(u) => { setUser(u); setHasPlan(false); }} />
      </main>
    );
  }

  // No active plan → the studio IS the subscribe flow: account → plan → payment.
  // The tabs stay unreachable until the plan activates ("no subscription, no studio").
  if (!hasPlan) {
    return (
      <main className="flex-1">
        <StudioSubscribeGate onActivated={() => setGateKey((k) => k + 1)} />
      </main>
    );
  }

  return (
    <main className="flex-1 bg-[var(--brand-black)] text-white">
      <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
        {/* top bar */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <LogoMark className="h-8 w-8" aria-hidden />
            <div>
              <h1 className="text-2xl md:text-3xl font-black uppercase tracking-tight leading-none">Your Studio</h1>
              <p className="text-xs text-white/50 uppercase tracking-widest mt-1">
                {user.name || user.email} - the engine at your fingertips
              </p>
            </div>
          </div>
        </div>

        {/* tabs */}
        <div className="mt-6 flex gap-1 overflow-x-auto border-b border-white/10 pb-px" role="tablist" aria-label="Studio sections">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-black uppercase tracking-widest whitespace-nowrap border-b-2 transition-colors ${
                tab === key ? "border-primary text-white" : "border-transparent text-white/50 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden /> {label}
            </button>
          ))}
        </div>

        <div className="mt-8">
          {tab === "create" && <CreateTab user={user} onSubmitted={() => setTab("queue")} />}
          {tab === "queue" && <QueueTab />}
          {tab === "videos" && <VideosLoader />}
          {tab === "profile" && <ProfileLoader user={user} onUserUpdated={setUser} onSignOut={() => setUser(null)} />}
          {tab === "support" && <SupportTab user={user} />}
        </div>
      </div>
    </main>
  );
}

/* ---------------- Subscribe gate (no active plan) ---------------- */

function StudioSubscribeGate({ onActivated }: { onActivated: () => void }) {
  const [data, setData] = useState<HomeData | null>(null);
  useEffect(() => {
    api<HomeData>("/api/home").then(setData).catch(() => setData(null));
  }, []);
  if (!data) {
    return (
      <div className="bg-[var(--brand-black)] text-white min-h-[70vh] grid place-items-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
      </div>
    );
  }
  return (
    <SubscribeView
      settings={data.settings ?? null}
      plans={data.plans ?? []}
      onActivated={onActivated}
    />
  );
}

/* ---------------- Create ---------------- */

function CreateTab({ user, onSubmitted }: { user: StudioUser; onSubmitted: () => void }) {
  const [models, setModels] = useState<StudioOverview["models"]>([]);
  const [engine, setEngine] = useState<StudioOverview["engine"] | null>(null);
  const [plan, setPlan] = useState<StudioOverview["plan"]>(null);
  const [loaded, setLoaded] = useState(false);
  const [used, setUsed] = useState(0);
  const [model, setModel] = useState("deyo.1");
  const [prompt, setPrompt] = useState("");
  const [seconds, setSeconds] = useState(15);
  const [voice, setVoice] = useState("");
  const [refImageUrl, setRefImageUrl] = useState("");
  const [refName, setRefName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");
  const { voices: licensed, reload: reloadLicensed } = useLicensedVoices();

  useEffect(() => {
    api<StudioOverview>("/api/studio/overview")
      .then((r) => {
        setModels(r.models);
        setEngine(r.engine);
        setPlan(r.plan);
        setUsed(r.used);
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const selected = models.find((m) => m.code === model);
  const cap = Math.min(selected?.secondsCap ?? 15, plan?.maxSecondsVideo ?? 15);

  useEffect(() => {
    if (seconds > cap) setSeconds(cap);
  }, [cap, seconds]);

  async function uploadRef(file: File) {
    setUploading(true);
    setRefName(file.name);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("kind", "character");
      const res = await api<{ url: string }>("/api/studio/upload", { method: "POST", body: fd });
      setRefImageUrl(res.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setOkMsg("");
    try {
      const res = await api<{ request: { id: string; fromCache: boolean; status: string } }>("/api/studio/requests", {
        method: "POST",
        body: JSON.stringify({ prompt, model, seconds, voice, refImageUrl }),
      });
      setOkMsg(
        res.request.fromCache
          ? "Delivered instantly - an identical render was in the cache. See Queue & My Videos."
          : "In the queue. Watch it move live in the Queue tab."
      );
      setPrompt("");
      setRefImageUrl("");
      setRefName("");
      setTimeout(onSubmitted, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid lg:grid-cols-[1fr_340px] gap-6 items-start">
      {loaded && !plan ? (
        /* No active plan → rendering stays locked. Subscribe to unlock. */
        <div className="border-2 border-primary/60 bg-primary/10 p-8 text-center" aria-label="Rendering locked">
          <Lock className="h-10 w-10 mx-auto text-primary" aria-hidden />
          <h2 className="mt-4 text-2xl font-black uppercase tracking-tight">Rendering is locked</h2>
          <p className="mt-3 text-sm text-white/70 leading-relaxed max-w-md mx-auto">
            Every DeYoung plan lives on an account - and this account doesn&apos;t have an active
            plan yet. Subscribe to unlock the model line, the queue and your licensed voices.
          </p>
          <Button onClick={() => go("#subscribe")} className="mt-6 h-12 px-8 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base">
            Choose a plan & subscribe <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
          <p className="mt-3 text-[11px] text-white/40 uppercase tracking-widest">Takes under a minute - plan attaches to this account</p>
        </div>
      ) : (
      <form onSubmit={submit} className="space-y-6">
        {/* model picker */}
        <div>
          <Label className="text-xs font-black uppercase tracking-widest text-white/70">1 - Pick your engine</Label>
          <div className="mt-3 grid sm:grid-cols-2 gap-2">
            {models.map((m) => (
              <button
                key={m.code}
                type="button"
                onClick={() => setModel(m.code)}
                aria-pressed={model === m.code}
                className={`text-left p-3.5 border-2 transition-colors ${
                  model === m.code ? "border-primary bg-primary/10" : "border-white/15 bg-white/5 hover:border-white/40"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="font-black tracking-tight">{m.name}</span>
                  {m.flagship && (
                    <span className="bg-primary text-white text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5">
                      Flagship
                    </span>
                  )}
                </span>
                <span className="block mt-1 text-[11px] text-white/60 leading-snug">{m.tagline}</span>
                <span className="block mt-2 text-[10px] font-bold uppercase tracking-widest text-white/40">
                  up to {m.secondsCap}s · {m.tier === "free" ? "local lane" : m.tier === "gpu" ? "GPU lane" : "priority lane"}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* script */}
        <div>
          <Label htmlFor="cr-script" className="text-xs font-black uppercase tracking-widest text-white/70">
            2 - Write the script
          </Label>
          <Textarea
            id="cr-script" required rows={5} value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the film you want - story, style, mood, on-screen text. The more specific, the better the cut."
            className="mt-3 bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary leading-relaxed"
          />
          <p className="mt-1.5 text-[11px] text-white/40">{prompt.length}/4000 characters</p>
        </div>

        {/* length */}
        <div>
          <Label htmlFor="cr-sec" className="text-xs font-black uppercase tracking-widest text-white/70">
            3 - Length: <span className="text-white">{seconds}s</span>
          </Label>
          <input
            id="cr-sec" type="range" min={5} max={cap} step={5} value={seconds}
            onChange={(e) => setSeconds(Number(e.target.value))}
            className="mt-3 w-full accent-[#DC2626]"
          />
          <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-white/40">
            <span>5s</span><span>{cap}s cap on {selected?.name ?? "this engine"}{plan ? ` & ${plan.name}` : ""}</span>
          </div>
        </div>

        {/* voice + character */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="cr-voice" className="text-xs font-black uppercase tracking-widest text-white/70">4 - Voice (optional)</Label>
            <select
              id="cr-voice" value={voice} onChange={(e) => setVoice(e.target.value)}
              className="mt-3 w-full h-10 bg-white/5 border border-white/20 text-white text-sm px-3 focus-visible:ring-primary"
            >
              {VOICES.map((v) => (
                <option key={v.code} value={v.code} className="bg-neutral-900">{v.label}</option>
              ))}
              {licensed.filter((v) => v.usable).length > 0 && (
                <optgroup label="My licensed voices">
                  {licensed.filter((v) => v.usable).map((v) => (
                    <option key={v.id} value={`clone:${v.id}`} className="bg-neutral-900">My voice - {v.label}</option>
                  ))}
                </optgroup>
              )}
            </select>
            <VoiceClonePanel user={user} onLicensed={reloadLicensed} />
          </div>
          <div>
            <Label className="text-xs font-black uppercase tracking-widest text-white/70">5 - Character / avatar reference (optional)</Label>
            <label className="mt-3 h-10 inline-flex items-center gap-2 border border-white/25 px-3 text-xs font-bold uppercase tracking-widest text-white/70 hover:text-white cursor-pointer w-full justify-center">
              {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Upload className="h-3.5 w-3.5" aria-hidden />}
              {uploading ? "Uploading…" : refImageUrl ? "Replace image" : "Upload image"}
              <input
                type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadRef(f); }}
              />
            </label>
            {refImageUrl && (
              <p className="mt-2 text-[11px] text-white/60 flex items-center gap-2">
                <Image src={refImageUrl} alt={refName || "reference"} width={28} height={28} className="object-cover border border-white/20" />
                <BadgeCheck className="h-3.5 w-3.5 text-primary" aria-hidden /> attached
              </p>
            )}
          </div>
        </div>

        {error && <p className="text-sm font-semibold text-primary" role="alert">{error}</p>}
        {okMsg && <p className="text-sm font-semibold text-white bg-white/10 border border-white/20 px-3 py-2">{okMsg}</p>}

        <Button type="submit" disabled={submitting || prompt.trim().length < 10}
          className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
          {submitting ? "Sending to the engine…" : "Render it - send to queue"}
        </Button>
      </form>
      )}

      {/* live engine side panel */}
      <aside className="space-y-4">
        <div className="border border-primary/60 bg-primary/10 p-4">
          <p className="text-xs font-black uppercase tracking-widest flex items-center gap-2">
            <Zap className="h-3.5 w-3.5" aria-hidden /> Your plan
          </p>
          {plan ? (
            <>
              <p className="mt-2 text-xl font-black">{plan.name}</p>
              <p className="text-xs text-white/70 mt-1">{used} of {plan.maxVideosMonth} videos used · up to {plan.maxSecondsVideo}s · {plan.maxResolution}</p>
              <div className="mt-3 h-1.5 bg-white/15">
                <div className="h-full bg-primary" style={{ width: `${Math.min(100, (used / Math.max(1, plan.maxVideosMonth)) * 100)}%` }} />
              </div>
            </>
          ) : (
            <>
              <p className="mt-2 text-sm text-white/80 leading-relaxed">No active subscription - pick a plan to unlock rendering. Your rate locks while you stay subscribed.</p>
              <Button onClick={() => go("#subscribe")} className="mt-3 w-full bg-primary hover:bg-[#B91C1C] text-white font-bold">Choose a plan</Button>
            </>
          )}
        </div>

        <div className="border border-white/15 bg-white/5 p-4">
          <p className="text-xs font-black uppercase tracking-widest flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-primary" aria-hidden /> Engine right now
          </p>
          {engine ? (
            <ul className="mt-3 space-y-2 text-sm text-white/70">
              <li className="flex items-center gap-2"><CircleDot className="h-3.5 w-3.5 text-primary" aria-hidden /> {engine.queued} queued</li>
              <li className="flex items-center gap-2"><Gauge className="h-3.5 w-3.5 text-primary" aria-hidden /> {engine.rendering} rendering</li>
              <li className="flex items-center gap-2"><Film className="h-3.5 w-3.5 text-primary" aria-hidden /> {engine.done24} delivered (24h)</li>
              <li className="flex items-center gap-2"><Clock className="h-3.5 w-3.5 text-primary" aria-hidden /> avg render {engine.avgRenderMin !== null ? `${engine.avgRenderMin} min` : "-"}</li>
            </ul>
          ) : (
            <p className="mt-3 text-sm text-white/50">Telemetry loading…</p>
          )}
          <p className="mt-3 text-[10px] leading-relaxed text-white/40 uppercase tracking-widest">
            Honest telemetry - computed from the real queue, live
          </p>
        </div>
      </aside>
    </div>
  );
}

/* ---------------- Queue (live) ---------------- */

function VideosLoader() {
  const [requests, setRequests] = useState<StudioRequest[] | null>(null);
  useLiveRequests(setRequests);
  if (!requests) return <CenterLoader />;
  return <VideosTab requests={requests} />;
}

function ProfileLoader({
  user, onUserUpdated, onSignOut,
}: {
  user: StudioUser;
  onUserUpdated: (u: StudioUser) => void;
  onSignOut: () => void;
}) {
  const [overview, setOverview] = useState<StudioOverview | null>(null);
  useEffect(() => {
    api<StudioOverview>("/api/studio/overview").then(setOverview).catch(() => {});
  }, []);
  return (
    <ProfileTab
      user={user}
      planName={overview?.plan?.name ?? null}
      used={overview?.used ?? 0}
      max={overview?.plan?.maxVideosMonth ?? null}
      onUserUpdated={onUserUpdated}
      onSignOut={async () => {
        await api("/api/user/logout", { method: "POST" }).catch(() => {});
        onSignOut();
      }}
    />
  );
}

function CenterLoader() {
  return (
    <div className="py-16 grid place-items-center">
      <Loader2 className="h-7 w-7 animate-spin text-primary" aria-hidden />
    </div>
  );
}

/** Polls /api/studio/requests every 4s while the tab is visible. */
function useLiveRequests(setter: (r: StudioRequest[]) => void) {
  const setterRef = useRef(setter);
  useEffect(() => {
    setterRef.current = setter;
  }, [setter]);
  const tick = useCallback(() => {
    api<{ requests: StudioRequest[] }>("/api/studio/requests")
      .then((r) => setterRef.current(r.requests))
      .catch(() => {});
  }, []);
  useEffect(() => {
    tick();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") tick();
    }, 4000);
    return () => clearInterval(t);
  }, [tick]);
}

function QueueTab() {
  const [requests, setRequests] = useState<StudioRequest[] | null>(null);
  const [engine, setEngine] = useState<StudioOverview["engine"] | null>(null);
  useLiveRequests(setRequests);
  useEffect(() => {
    api<StudioOverview>("/api/studio/overview").then((r) => setEngine(r.engine)).catch(() => {});
    const t = setInterval(() => {
      api<StudioOverview>("/api/studio/overview").then((r) => setEngine(r.engine)).catch(() => {});
    }, 8000);
    return () => clearInterval(t);
  }, []);

  if (!requests) return <CenterLoader />;

  const active = requests.filter((r) => r.status === "queued" || r.status === "rendering");
  const past = requests.filter((r) => r.status !== "queued" && r.status !== "rendering").slice(0, 8);

  return (
    <div className="space-y-8">
      {/* engine strip */}
      {engine && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <EngineChip icon={CircleDot} label="Queued" value={String(engine.queued)} />
          <EngineChip icon={Gauge} label="Rendering" value={String(engine.rendering)} />
          <EngineChip icon={Film} label="Delivered 24h" value={String(engine.done24)} />
          <EngineChip icon={Clock} label="Avg render" value={engine.avgRenderMin !== null ? `${engine.avgRenderMin}m` : "-"} />
        </div>
      )}

      {active.length === 0 ? (
        <EmptyState
          title="Queue is clear"
          body="Nothing is waiting on the engine right now. Send a script from the Create tab and watch it move here in real time."
        />
      ) : (
        <div className="space-y-3">
          {active.map((r) => (
            <QueueCard key={r.id} r={r} />
          ))}
        </div>
      )}

      {past.length > 0 && (
        <div>
          <p className="text-xs font-black uppercase tracking-widest text-white/50">Recent history</p>
          <div className="mt-3 space-y-2">
            {past.map((r) => (
              <div key={r.id} className="border border-white/10 bg-white/5 px-4 py-3 flex items-center gap-3">
                <StatusDot status={r.status} />
                <p className="text-sm font-semibold flex-1 min-w-0 truncate">{r.prompt}</p>
                <span className="text-[10px] font-black uppercase tracking-widest text-white/40 whitespace-nowrap">
                  {r.model} · {r.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EngineChip({ icon: Icon, label, value }: { icon: typeof Film; label: string; value: string }) {
  return (
    <div className="border border-white/15 bg-white/5 px-3 py-2.5 flex items-center gap-3">
      <Icon className="h-4 w-4 text-primary shrink-0" aria-hidden />
      <div className="min-w-0">
        <p className="text-lg font-black leading-none">{value}</p>
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/50 truncate">{label}</p>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "done" ? "bg-green-500" :
    status === "failed" || status === "cancelled" ? "bg-red-500" :
    status === "rendering" ? "bg-primary animate-pulse" : "bg-white/40";
  return <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${color}`} aria-hidden />;
}

function QueueCard({ r }: { r: StudioRequest }) {
  const rendering = r.status === "rendering";
  const pct = rendering ? Math.max(4, Math.min(99, r.progress || 4)) : 0;
  return (
    <div className={`border-2 p-4 ${rendering ? "border-primary/70 bg-primary/5" : "border-white/15 bg-white/5"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-bold leading-snug line-clamp-2">{r.prompt}</p>
          <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-white/50">
            {r.model} · {r.seconds}s · {r.resolution}{r.voice ? ` · voice: ${r.voice}` : ""}
          </p>
        </div>
        <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-1 whitespace-nowrap ${
          rendering ? "bg-primary text-white" : "bg-white/15 text-white/80"
        }`}>
          {rendering ? "rendering" : `queue #${r.queuePosition ?? "-"}`}
        </span>
      </div>

      {rendering ? (
        <div className="mt-3">
          <div className="h-2 bg-white/10 overflow-hidden">
            <div className="h-full bg-primary transition-all duration-700" style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-[10px] font-bold uppercase tracking-widest text-white/60">
            <span>{r.stage || "working"}…</span>
            <span>{pct}%</span>
          </div>
        </div>
      ) : (
        <p className="mt-2 text-[11px] text-white/50 leading-relaxed">
          Waiting for a worker{r.queuePosition && r.queuePosition > 1 ? ` - ${r.queuePosition - 1} ahead of you` : " - you're next"}. Positions update live.
        </p>
      )}
    </div>
  );
}

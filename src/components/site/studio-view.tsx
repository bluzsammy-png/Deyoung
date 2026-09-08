"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/types";
import { go } from "@/components/site/hash";
import { useSessionBadge } from "@/components/site/use-session";
import { AgentStream } from "@/components/site/agent-stream";
import {
  ArrowRight,
  Check,
  Clapperboard,
  Film,
  Loader2,
  MonitorPlay,
  Radio,
  Save,
  Sparkles,
  Wand2,
  Users,
  Layers,
} from "lucide-react";

/**
 * W3 — the DeYoung AI Film Studio, workstation edition.
 * A three-zone cinema console: the Director's Console (brief controls) on the
 * left, a dot-grid workflow canvas (script → scenes → delivery) in the center
 * with animated node ports and flowing edges, and the live render queue on the
 * right. Every node is interactive: the enhancer rewrites the prompt, the
 * writer turns the brief into a full script (characters + scenes), and each
 * scene can be pushed to the render fleet. Admins run it free with unlimited
 * quota. Logic identical to W2 — presentation upgraded to H3-studio grade.
 */

const NICHES = [
  "kids cartoon",
  "product ad",
  "real estate",
  "music video",
  "explainer",
  "social reel",
  "travel",
  "fashion",
  "gaming",
  "custom",
];

type Script = {
  title: string;
  logline: string;
  characters: { name: string; look: string; voice: string }[];
  scenes: {
    id: string;
    title: string;
    seconds: number;
    line: string;
    visual: string;
    direction?: {
      shot: string;
      move: string;
      light: string;
      composition: string;
      emotion: string;
      sound: string;
      principle: string;
      note: string;
    };
  }[];
  bible?: {
    styleAnchor: string;
    palette: string;
    lightPhilosophy: string;
    lensFeel: string;
    directorVoice: string;
    kidPromise: string;
    bibleLine: string;
  };
};

/** Character sheets + per-scene keyframes produced by the render fleet.
 *  urls are /api/files/{assetId} links (storyboard stills are public assets). */
type Storyboard = {
  sheets: { name: string; url: string }[];
  keyframes: { scene: string; url: string }[];
};

type Me = {
  blocked?: { status: string; reason: string };
  unlimited?: boolean;
  subscription: { planCode: string; status: string } | null;
  plan: { maxSecondsVideo: number; maxResolution: string; audio: boolean } | null;
};

type RenderState = Record<string, { requestId: string; status: string; resultUrl?: string; etaDays?: number }>;

/* ---------- workflow primitives ---------- */

function PortDot({ on, className = "" }: { on: boolean; className?: string }) {
  return (
    <span
      aria-hidden
      className={`dy-port absolute left-1/2 -translate-x-1/2 ${on ? "dy-port-on" : ""} ${className}`}
    />
  );
}

/** Animated data-flow edge between canvas nodes. */
function FlowEdge({ active }: { active: boolean }) {
  return (
    <div className="flex justify-center py-0.5" aria-hidden>
      <svg width="22" height="36" viewBox="0 0 22 36" className={active ? "text-brand-red" : "text-white/20"}>
        <path
          d="M11 1 C 11 13, 11 23, 11 34"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={active ? "6 5" : "4 4"}
          className={active ? "dy-flow" : ""}
        />
        <path d="M6 28 L11 35 L16 28" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function NodeShell({
  step,
  title,
  sub,
  icon,
  active,
  done,
  children,
}: {
  step: string;
  title: string;
  sub?: string;
  icon: React.ReactNode;
  active: boolean;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`dy-node relative p-5 md:p-6 ${active ? "dy-node-active" : ""} ${done && !active ? "dy-node-done" : ""}`}>
      <PortDot on={active} className="-top-[5px]" />
      <div className="flex items-center gap-3">
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-xl border ${
            active || done
              ? "border-primary/60 bg-primary/15 text-primary shadow-[0_0_18px_-4px_rgba(220,38,38,0.7)]"
              : "border-white/15 text-white/40"
          }`}
        >
          {done && !active ? <Check className="h-4 w-4" aria-hidden /> : icon}
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/35">
            Node {step} {sub ? `· ${sub}` : ""}
          </p>
          <h3 className="truncate text-lg font-black uppercase leading-tight">{title}</h3>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function StatusPill({ status, etaDays }: { status: string; etaDays?: number }) {
  const cls =
    status === "done"
      ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
      : status === "failed" || status === "cancelled"
        ? "border-red-500/30 bg-red-500/15 text-red-400"
        : "border-amber-500/30 bg-amber-500/15 text-amber-400";
  const busy = status === "queued" || status === "rendering";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${cls}`}>
      {busy && <span className="dy-busy-dot" aria-hidden />}
      {status}
      {status === "queued" && etaDays ? ` · ~${etaDays}d` : ""}
    </span>
  );
}

export function StudioView({ projectId }: { projectId?: string }) {
  const session = useSessionBadge();
  const [me, setMe] = useState<Me | null>(null);
  const [authErr, setAuthErr] = useState<string | null>(null);

  const [niche, setNiche] = useState("kids cartoon");
  const [brief, setBrief] = useState("");
  const [enhanced, setEnhanced] = useState("");
  const [enhancing, setEnhancing] = useState(false);
  const [writing, setWriting] = useState(false);
  const [script, setScript] = useState<Script | null>(null);
  const [title, setTitle] = useState("");
  const [savedId, setSavedId] = useState<string | undefined>(projectId);
  const [saving, setSaving] = useState(false);
  const [render, setRender] = useState<RenderState>({});
  const [watch, setWatch] = useState<string | null>(null); // requestId of the live-run console
  const [err, setErr] = useState<string | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [filmLength, setFilmLength] = useState<number>(15);
  const [renderingAll, setRenderingAll] = useState(false);
  const restored = useRef(false);

  const unlimited = Boolean(me?.unlimited);
  // Owner tier: plan is synthetic (null) — give the studio a real 120s film
  // budget instead of falling back to the 15s default that produced 3x5s films.
  const maxSeconds = unlimited ? 120 : (me?.plan?.maxSecondsVideo ?? 15);
  const maxRes = unlimited ? "1080p" : (me?.plan?.maxResolution ?? "720p");

  useEffect(() => {
    api<Me>("/api/me")
      .then((d) => {
        if (d.blocked) setAuthErr(`Account ${d.blocked.status}: ${d.blocked.reason}`);
        else setMe(d);
      })
      .catch((e) => setAuthErr(e instanceof Error ? e.message : "Sign in to use the studio"));
  }, []);

  // restore a saved project (+ its fleet-generated storyboard)
  useEffect(() => {
    if (!projectId || restored.current) return;
    restored.current = true;
    api<{ projects: { id: string; title: string; niche: string; brief: string; scriptJson: string; storyboardJson: string | null }[] }>(
      "/api/studio/projects"
    )
      .then((d) => {
        const p = d.projects.find((x) => x.id === projectId);
        if (!p) return;
        setSavedId(p.id);
        setTitle(p.title);
        setNiche(p.niche || "custom");
        setBrief(p.brief);
        try {
          const parsed = JSON.parse(p.scriptJson) as Script;
          if (parsed?.scenes?.length) setScript(parsed);
        } catch { /* draft without script */ }
        try {
          if (p.storyboardJson) setStoryboard(JSON.parse(p.storyboardJson) as Storyboard);
        } catch { /* no storyboard yet */ }
      })
      .catch(() => undefined);
  }, [projectId]);

  // pick up the storyboard once the fleet generates it (poll while rendering)
  useEffect(() => {
    if (!savedId || storyboard) return;
    const t = setInterval(() => {
      api<{ projects: { id: string; storyboardJson: string | null }[] }>("/api/studio/projects")
        .then((d) => {
          const p = d.projects.find((x) => x.id === savedId);
          if (p?.storyboardJson) {
            try { setStoryboard(JSON.parse(p.storyboardJson) as Storyboard); } catch { /* ignore */ }
          }
        })
        .catch(() => undefined);
    }, 20000);
    return () => clearInterval(t);
  }, [savedId, storyboard]);

  // live render status (film-simulator feel)
  const pollRenders = useCallback(() => {
    setRender((cur) => {
      const pending = Object.entries(cur).filter(([, v]) => v.status === "queued" || v.status === "rendering");
      if (pending.length === 0) return cur;
      api<{ requests: { id: string; status: string; resultUrl: string }[] }>("/api/me").then((d) => {
        if (!d.requests) return;
        setRender((cur2) => {
          const next = { ...cur2 };
          for (const [, v] of Object.entries(next)) {
            const hit = d.requests.find((r) => r.id === v.requestId);
            if (hit && hit.status !== v.status) {
              next[v.requestId] = { ...v, status: hit.status, resultUrl: hit.resultUrl || v.resultUrl };
            }
          }
          return next;
        });
      }).catch(() => undefined);
      return cur;
    });
  }, []);
  useEffect(() => {
    const t = setInterval(pollRenders, 8000);
    return () => clearInterval(t);
  }, [pollRenders]);

  async function enhance() {
    setEnhancing(true);
    setErr(null);
    try {
      const d = await api<{ enhanced: string }>("/api/studio/enhance", {
        method: "POST",
        body: JSON.stringify({ prompt: brief || enhanced, niche }),
      });
      setEnhanced(d.enhanced);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Enhancer failed");
    } finally {
      setEnhancing(false);
    }
  }

  async function writeScript() {
    setWriting(true);
    setErr(null);
    try {
      const d = await api<{ script: Script }>("/api/studio/script", {
        method: "POST",
        body: JSON.stringify({ brief: enhanced || brief, niche, seconds: Math.min(maxSeconds, filmLength) }),
      });
      setScript(d.script);
      setTitle(d.script.title);
      setStoryboard(null); // a new script invalidates the old storyboard
      setTimeout(() => saveProject(d.script), 50);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Script writer failed");
    } finally {
      setWriting(false);
    }
  }

  async function renderAllScenes() {
    if (!script) return;
    setRenderingAll(true);
    try {
      for (const sc of script.scenes) {
        const r = render[sc.id];
        if (r && !["failed", "cancelled"].includes(r.status)) continue; // already queued/rendered
        await submitScene(sc, unlimited ? "1080p" : maxRes, unlimited ? true : Boolean(me?.plan?.audio));
      }
    } finally {
      setRenderingAll(false);
    }
  }

  const saveProject = useCallback(
    async (currentScript?: Script | null) => {
      setSaving(true);
      try {
        const d = await api<{ project: { id: string } }>("/api/studio/projects", {
          method: "POST",
          body: JSON.stringify({
            id: savedId,
            title: title || currentScript?.title || "Untitled film",
            niche,
            brief,
            scriptJson: JSON.stringify(currentScript ?? script ?? {}),
            status: currentScript || script ? "scripted" : "draft",
          }),
        });
        setSavedId(d.project.id);
      } catch {
        /* keep editing even if autosave hiccups */
      } finally {
        setSaving(false);
      }
    },
    [brief, niche, savedId, script, title]
  );

  async function submitScene(scene: { id: string; seconds: number; visual: string; line: string }, resolution: string, withAudio: boolean) {
    setErr(null);
    const prompt = enhanced || brief
      ? `${enhanced || brief} — Scene ${scene.id}: ${scene.visual} ${scene.line ? `Line: "${scene.line}"` : ""}`.trim()
      : `${scene.visual} ${scene.line ? `Line: "${scene.line}"` : ""}`.trim();
    try {
      const d = await api<{ request: { id: string; status: string }; etaDays: number }>("/api/studio/render", {
        method: "POST",
        // clamp to the API floor (5s) — scripts written before the writer-side
        // floor fix may contain shorter scenes
        body: JSON.stringify({ prompt, seconds: Math.max(5, scene.seconds), resolution, withAudio, projectId: savedId, sceneId: scene.id }),
      });
      setRender((cur) => ({ ...cur, [`${scene.id}`]: { requestId: d.request.id, status: d.request.status, etaDays: d.etaDays } }));
      setWatch(d.request.id); // open the live film-simulator console immediately
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Render submit failed");
    }
  }

  const activeScene = useMemo(() => script?.scenes[0], [script]);
  const stepsDone = { brief: brief.length > 10 || enhanced.length > 10, script: Boolean(script) };
  const renderCounts = useMemo(() => {
    const vals = Object.values(render);
    return {
      busy: vals.filter((r) => ["queued", "rendering"].includes(r.status)).length,
      done: vals.filter((r) => r.status === "done").length,
      total: vals.length,
    };
  }, [render]);

  if (authErr) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] px-4 py-24 text-center text-white">
        <Clapperboard className="mx-auto h-10 w-10 text-primary" aria-hidden />
        <p className="mt-4 text-2xl font-black uppercase">The studio needs you signed in</p>
        <p className="mx-auto mt-2 max-w-md text-white/60">{authErr}</p>
        <div className="mt-6 flex justify-center gap-2">
          <Button onClick={() => go("/signin")} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">Sign in</Button>
          <Button onClick={() => go("/signup")} variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
            Create account
          </Button>
        </div>
      </div>
    );
  }
  if (!me) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[var(--brand-black)] text-white">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-label="Loading studio" />
      </div>
    );
  }

  const needsPlan = !unlimited && !me.subscription;
  const totalSceneSeconds = script?.scenes.reduce((a, s) => a + s.seconds, 0) ?? 0;

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[var(--brand-black)] pb-20 text-white">
      {/* ---------- top strip ---------- */}
      <div className="mx-auto max-w-[1440px] px-4 pt-8 md:pt-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.3em] text-primary">
              <Clapperboard className="h-4 w-4" aria-hidden /> DeYoung AI Film Studio
            </p>
            <h1 className="mt-1 text-3xl font-black uppercase md:text-4xl">Watch the agent build your film</h1>
            <p className="mt-2 max-w-xl text-sm text-white/50">
              Brief the director on the console. The agent enhances your prompt, writes the script, casts the
              characters and pushes scenes down the workflow — every port live, every edge flowing.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${unlimited ? "border-primary/50 bg-primary/10 text-primary" : "border-white/15 text-white/60"}`}>
              {unlimited ? "Owner · Free ∞" : me.plan ? me.plan.maxSecondsVideo + "s · " + me.plan.maxResolution : "No plan"}
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-bold text-white/55">
              {saving ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Saving…
                </span>
              ) : savedId ? (
                <span className="inline-flex items-center gap-1.5">
                  <Check className="h-3 w-3 text-emerald-400" aria-hidden /> Project saved
                </span>
              ) : (
                "Draft"
              )}
            </span>
            <Button size="sm" variant="outline" onClick={() => saveProject()} disabled={saving} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Save className="h-4 w-4" aria-hidden />}
              Save
            </Button>
          </div>
        </div>

        {needsPlan && (
          <div className="mt-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-300">
            You can write and storyboard freely — submitting renders needs an active plan.{" "}
            <a href="#/subscribe" className="font-black underline">Choose a plan →</a>
          </div>
        )}
        {err && <p className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm font-semibold text-red-400">{err}</p>}
      </div>

      {/* ---------- workstation: console | canvas | queue ---------- */}
      <div className="mx-auto grid max-w-[1440px] items-start gap-5 px-4 py-8 lg:grid-cols-[330px_minmax(0,1fr)_330px]">
        {/* LEFT RAIL — the director's console (brief inputs) */}
        <aside className="dy-scroll-y space-y-4 self-start lg:sticky lg:top-[84px] lg:max-h-[calc(100vh-104px)] lg:overflow-y-auto lg:pr-1">
          <NodeShell step="01" sub="input" title="Brief console" icon={<Wand2 className="h-4 w-4" aria-hidden />} active={!stepsDone.brief} done={stepsDone.brief}>
            <p className="mb-3 text-sm text-white/50">Pick a niche — the whole pipeline tunes itself to it.</p>
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Niche">
              {NICHES.map((n) => (
                <button
                  key={n}
                  role="radio"
                  aria-checked={niche === n}
                  onClick={() => setNiche(n)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-bold capitalize transition-colors ${
                    niche === n ? "border-primary bg-primary/15 text-primary" : "border-white/15 text-white/60 hover:border-white/30"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="mt-4 space-y-1.5">
              <Label htmlFor="st-brief" className="text-white/70">Your idea</Label>
              <Textarea
                id="st-brief"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                rows={4}
                placeholder="A boy discovers his drawing pen brings cartoons to life…"
                className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
              />
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Label htmlFor="st-len" className="shrink-0 text-[10px] font-black uppercase tracking-widest text-white/40">
                Film length
              </Label>
              <select
                id="st-len"
                value={filmLength}
                onChange={(e) => setFilmLength(Number(e.target.value))}
                className="w-full rounded-lg border border-white/15 bg-white/5 px-2 py-1.5 text-sm font-bold text-white"
                aria-label="Film length"
              >
                {[15, 30, 45, 60, 90, 120].filter((s) => s <= maxSeconds).map((s) => (
                  <option key={s} value={s} className="bg-neutral-900">{s}s</option>
                ))}
              </select>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={enhance} disabled={enhancing || brief.trim().length < 8} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
                {enhancing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Sparkles className="h-4 w-4" aria-hidden />}
                Enhance with AI
              </Button>
              <Button
                onClick={writeScript}
                disabled={writing || (brief.trim().length < 10 && enhanced.trim().length < 10)}
                variant="outline"
                className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
              >
                {writing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Film className="h-4 w-4" aria-hidden />}
                Write the script
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            {enhanced && (
              <div className="mt-4 rounded-xl border border-primary/30 bg-primary/[0.07] p-4">
                <p className="text-[10px] font-black uppercase tracking-widest text-primary">Agent-enhanced prompt</p>
                <p className="mt-2 text-sm leading-relaxed text-white/85">{enhanced}</p>
                <button onClick={() => setBrief(enhanced)} className="mt-2 text-xs font-bold text-primary hover:underline">
                  Use as brief →
                </button>
              </div>
            )}
          </NodeShell>

          {/* workflow map */}
          <div className="dy-node p-4">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/35">Workflow map</p>
            <div className="mt-3 space-y-2">
              {[
                { n: "01", label: "Brief", on: stepsDone.brief },
                { n: "02", label: "Script", on: Boolean(script) },
                { n: "03", label: "Render", on: renderCounts.total > 0 },
                { n: "04", label: "Deliver", on: renderCounts.total > 0 && renderCounts.done === renderCounts.total },
              ].map((s, i) => (
                <div key={s.n} className="flex items-center gap-2.5">
                  <span className={`flex h-6 w-8 items-center justify-center rounded-md border text-[10px] font-black ${
                    s.on ? "border-primary/50 bg-primary/15 text-primary" : "border-white/15 text-white/35"
                  }`}>
                    {s.n}
                  </span>
                  <span className={`text-xs font-bold uppercase tracking-wider ${s.on ? "text-white/85" : "text-white/40"}`}>{s.label}</span>
                  <span className={`h-1.5 flex-1 rounded-full ${s.on ? "bg-primary/60" : "bg-white/10"}`} />
                  {i < 3 && <ArrowRight className={`h-3 w-3 ${s.on ? "text-primary/70" : "text-white/20"}`} aria-hidden />}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* CENTER — the workflow canvas */}
        <main className="dy-canvas relative rounded-3xl border border-white/10 bg-white/[0.015] p-4 md:p-6">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/35">Workflow canvas</p>
            <p className={`text-[10px] font-bold uppercase tracking-widest ${renderCounts.busy > 0 ? "text-amber-400" : "text-white/40"}`}>
              {renderCounts.busy > 0 ? `${renderCounts.busy} node${renderCounts.busy > 1 ? "s" : ""} rendering` : "idle · ready"}
            </p>
          </div>

          {/* NODE 02 — SCRIPT */}
          <NodeShell
            step="02"
            sub="agent"
            title={script ? script.title : "The script"}
            icon={<Film className="h-4 w-4" aria-hidden />}
            active={Boolean(script)}
            done={Boolean(script)}
          >
            {!script ? (
              <p className="text-sm text-white/40">
                The agent will split your brief into scenes with camera direction, cast the characters and write one
                line per shot. Press <span className="font-bold text-white/70">Write the script</span> on the console.
              </p>
            ) : (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    aria-label="Film title"
                    className="border-white/15 bg-white/5 text-lg font-black text-white"
                  />
                  <p className="text-sm italic text-white/50">{script.logline}</p>
                </div>
                {script.characters.length > 0 && (
                  <div>
                    <p className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-white/40">
                      <Users className="h-3.5 w-3.5" aria-hidden /> Cast
                    </p>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                      {script.characters.map((c) => (
                        <div key={c.name} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                          <p className="font-black">{c.name}</p>
                          <p className="mt-1 text-xs text-white/50">{c.look}</p>
                          {c.voice && <p className="mt-1 text-xs text-primary/80">voice: {c.voice}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {storyboard && (
                  <div className="rounded-xl border border-primary/30 bg-primary/[0.05] p-4">
                    <p className="text-[11px] font-black uppercase tracking-widest text-primary">
                      Storyboard — drawn by the fleet
                    </p>
                    {storyboard.sheets?.length > 0 && (
                      <>
                        <p className="mt-2 text-xs text-white/50">Character sheets (the cast, created from scratch):</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-3">
                          {storyboard.sheets.map((s) => (
                            <figure key={s.url} className="overflow-hidden rounded-lg border border-white/10">
                              { }
                              <img src={s.url} alt={`Character sheet — ${s.name}`} className="aspect-square w-full object-cover" />
                              <figcaption className="bg-white/5 px-2 py-1 text-xs font-bold">{s.name}</figcaption>
                            </figure>
                          ))}
                        </div>
                      </>
                    )}
                    {storyboard.keyframes?.length > 0 && (
                      <>
                        <p className="mt-3 text-xs text-white/50">Scene keyframes (each scene starts from its keyframe — that&apos;s how characters stay consistent):</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                          {storyboard.keyframes.map((k) => (
                            <figure key={k.url} className="overflow-hidden rounded-lg border border-white/10">
                              { }
                              <img src={k.url} alt={`Keyframe — scene ${k.scene}`} className="aspect-video w-full object-cover" />
                              <figcaption className="bg-white/5 px-2 py-1 text-xs font-bold">Scene {k.scene}</figcaption>
                            </figure>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
                <p className="text-xs text-white/40">
                  {script.scenes.length} scenes · {totalSceneSeconds}s total
                </p>
              </div>
            )}
          </NodeShell>

          <FlowEdge active={Boolean(script)} />

          {/* NODE 03 — SCENES → FLEET */}
          {script && (
            <NodeShell
              step="03"
              sub="fleet"
              title="Scenes → render queue"
              icon={<Clapperboard className="h-4 w-4" aria-hidden />}
              active
            >
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-white/40">
                    {renderCounts.busy > 0
                      ? "The fleet renders scene by scene — monitor any scene from the queue rail."
                      : "Every scene renders with its keyframe + cast for a consistent film."}
                  </p>
                  {script.scenes.length > 1 && (
                    <Button
                      size="sm"
                      onClick={renderAllScenes}
                      disabled={renderingAll || !unlimited && !me?.subscription}
                      className="bg-primary font-bold text-white hover:bg-[#B91C1C]"
                    >
                      {renderingAll ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Clapperboard className="h-3.5 w-3.5" aria-hidden />}
                      Render all {script.scenes.length} scenes
                    </Button>
                  )}
                </div>
                {script.bible && (
                  <div className="rounded-xl border border-primary/25 bg-primary/[0.06] p-4">
                    <p className="text-[11px] font-black uppercase tracking-widest text-primary">The Director&apos;s Brain — this film&apos;s visual bible</p>
                    <p className="mt-1 text-xs leading-relaxed text-white/70">{script.bible.bibleLine}</p>
                  </div>
                )}
                {script.scenes.map((sc) => {
                  const r = render[sc.id];
                  return (
                    <div key={sc.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-black">
                          {sc.id} · {sc.title} <span className="text-white/40">({sc.seconds}s)</span>
                        </p>
                        {r && <StatusPill status={r.status} etaDays={r.etaDays} />}
                      </div>
                      <p className="mt-2 text-sm text-white/70">{sc.visual}</p>
                      {sc.line && <p className="mt-1 text-sm italic text-primary/90">“{sc.line}”</p>}
                      {sc.direction && (
                        <div className="mt-2 space-y-1">
                          <div className="flex flex-wrap gap-1.5">
                            {[
                              sc.direction.shot,
                              sc.direction.move,
                              sc.direction.emotion ? `feeling: ${sc.direction.emotion}` : "",
                              sc.direction.principle?.split(" — ")[0] ? `principle: ${sc.direction.principle.split(" — ")[0]}` : "",
                            ]
                              .filter(Boolean)
                              .map((badge) => (
                                <span key={badge as string} className="rounded-full border border-white/15 bg-white/[0.06] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white/70">
                                  {badge}
                                </span>
                              ))}
                          </div>
                          <p className="text-xs leading-relaxed text-white/45">
                            <span className="font-black uppercase tracking-wide text-primary/80">Director&apos;s note:</span> {sc.direction.note}
                          </p>
                        </div>
                      )}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {storyboard?.keyframes?.find((k) => k.scene === sc.id) && (
                           
                          <img
                            src={storyboard.keyframes.find((k) => k.scene === sc.id)!.url}
                            alt={`Keyframe for ${sc.id}`}
                            className="h-14 w-24 rounded-md border border-white/10 object-cover"
                          />
                        )}
                        <Button size="sm" onClick={() => submitScene(sc, unlimited ? "1080p" : maxRes, unlimited ? true : Boolean(me?.plan?.audio))} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
                          <Clapperboard className="h-3.5 w-3.5" aria-hidden /> Render scene
                        </Button>
                        {unlimited && (
                          <Button size="sm" variant="outline" onClick={() => submitScene(sc, "1080p", true)} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                            1080p + audio
                          </Button>
                        )}
                        {r && ["queued", "rendering"].includes(r.status) && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setWatch(r.requestId)}
                            className="border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 hover:text-amber-200"
                          >
                            <Radio className="h-3.5 w-3.5" aria-hidden /> Watch live
                          </Button>
                        )}
                        {r?.status === "done" && r.resultUrl && (
                          <a href={r.resultUrl} target="_blank" rel="noreferrer" className="text-xs font-bold text-primary hover:underline">
                            Watch →
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </NodeShell>
          )}

          {script && <FlowEdge active={renderCounts.done > 0} />}

          {/* NODE 04 — DELIVERY */}
          {script && (
            <NodeShell
              step="04"
              sub="output"
              title="Delivery"
              icon={<Check className="h-4 w-4" aria-hidden />}
              active={renderCounts.done > 0}
              done={renderCounts.total > 0 && renderCounts.done === renderCounts.total}
            >
              <p className="text-sm text-white/50">
                {renderCounts.done}/{renderCounts.total} scenes delivered. Renders land here and in your{" "}
                <button onClick={() => go("/dashboard")} className="font-bold text-primary hover:underline">dashboard</button> — status polls live.
                {unlimited ? " Owner queue priority: first, always." : ""}
              </p>
              {activeScene && renderCounts.total === 0 && (
                <p className="mt-2 text-sm text-white/40">Start with {activeScene.id} — the establishing shot.</p>
              )}
            </NodeShell>
          )}

          {/* LIVE MONITOR — docked film simulator */}
          {watch && (
            <div className="mt-5 overflow-hidden rounded-2xl border border-primary/30 bg-black/50 shadow-[0_0_60px_-18px_rgba(220,38,38,0.55)]">
              <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
                <p className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-primary">
                  <MonitorPlay className="h-3.5 w-3.5" aria-hidden /> Live monitor — the agent at work
                </p>
                <span className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-red-400">
                  <span className="dy-busy-dot" aria-hidden /> On air
                </span>
              </div>
              <div className="p-3">
                <AgentStream requestId={watch} onClose={() => setWatch(null)} />
              </div>
            </div>
          )}
        </main>

        {/* RIGHT RAIL — live render queue */}
        <aside className="dy-scroll-y space-y-4 self-start lg:sticky lg:top-[84px] lg:max-h-[calc(100vh-104px)] lg:overflow-y-auto lg:pl-1">
          <div className="dy-node p-4">
            <div className="flex items-center justify-between">
              <p className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-white/35">
                <Layers className="h-3.5 w-3.5" aria-hidden /> Render queue
              </p>
              <div className="flex items-center gap-1.5">
                {renderCounts.busy > 0 && (
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-black uppercase text-amber-400">
                    {renderCounts.busy} busy
                  </span>
                )}
                {renderCounts.done > 0 && (
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-black uppercase text-emerald-400">
                    {renderCounts.done} done
                  </span>
                )}
              </div>
            </div>
            {!script ? (
              <p className="mt-3 text-sm text-white/40">
                The queue wakes up when your script exists — every scene shows its fleet status here in real time.
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {script.scenes.map((sc) => {
                  const r = render[sc.id];
                  const kf = storyboard?.keyframes?.find((k) => k.scene === sc.id);
                  return (
                    <div key={sc.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                      <div className="flex items-center gap-2.5">
                        {kf ? (
                           
                          <img src={kf.url} alt={`Keyframe ${sc.id}`} className="h-10 w-16 shrink-0 rounded-md border border-white/10 object-cover" />
                        ) : (
                          <span className="flex h-10 w-16 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.04] text-white/30">
                            <Film className="h-3.5 w-3.5" aria-hidden />
                          </span>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-black">{sc.id} · {sc.title}</p>
                          <p className="text-[10px] uppercase tracking-wider text-white/40">{sc.seconds}s shot</p>
                        </div>
                        <StatusPill status={r?.status ?? "not queued"} etaDays={r?.etaDays} />
                      </div>
                      {r && ["queued", "rendering"].includes(r.status) && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setWatch(r.requestId)}
                          className="mt-2 h-7 w-full border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 hover:text-amber-200"
                        >
                          <Radio className="h-3 w-3" aria-hidden /> Monitor live
                        </Button>
                      )}
                      {r?.status === "done" && r.resultUrl && (
                        <a href={r.resultUrl} target="_blank" rel="noreferrer" className="mt-2 block text-center text-[11px] font-bold text-primary hover:underline">
                          Open film →
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {needsPlan ? (
            <div className="dy-node border-amber-500/30 p-4">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-amber-400">Unlock the fleet</p>
              <p className="mt-2 text-sm text-white/70">
                Your renders ride the DeYoung GPU fleet. Pick a plan to push scenes to the queue.
              </p>
              <a href="#/subscribe" className="mt-3 inline-block rounded-lg bg-primary px-3 py-1.5 text-xs font-black uppercase tracking-wider text-white hover:bg-[#B91C1C]">
                Choose a plan →
              </a>
            </div>
          ) : (
            <div className="dy-node p-4">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/35">Your rig</p>
              <p className="mt-2 text-sm font-bold">
                {unlimited ? "Owner rig — unlimited seconds, 1080p + audio, top queue priority." :
                  me.plan ? `${me.plan.maxSecondsVideo}s films · ${me.plan.maxResolution}${me.plan.audio ? " · audio on" : ""}` : "No plan"}
              </p>
              <p className="mt-1 text-xs text-white/40">Status polls every 8s while the fleet works.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}


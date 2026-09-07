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
  Radio,
  Save,
  Sparkles,
  Wand2,
  Users,
} from "lucide-react";

/**
 * W2 — the DeYoung AI Film Studio.
 * A live agent pipeline: Brief → Script → Scenes → Characters → Render →
 * Deliver, drawn as a connected storyboard. Every node is interactive:
 * the enhancer rewrites the prompt, the writer turns the brief into a full
 * script (characters + scenes), and each scene can be pushed to the render
 * queue. Admins run it free with unlimited quota.
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
  scenes: { id: string; title: string; seconds: number; line: string; visual: string }[];
};

type Me = {
  blocked?: { status: string; reason: string };
  unlimited?: boolean;
  subscription: { planCode: string; status: string } | null;
  plan: { maxSecondsVideo: number; maxResolution: string; audio: boolean } | null;
};

type RenderState = Record<string, { requestId: string; status: string; resultUrl?: string; etaDays?: number }>;

/* ---------- pipeline connector ---------- */
function Connector({ active }: { active: boolean }) {
  return (
    <div className="flex justify-center py-1" aria-hidden>
      <svg width="24" height="28" viewBox="0 0 24 28" className={active ? "text-primary" : "text-white/20"}>
        <line x1="12" y1="0" x2="12" y2="20" stroke="currentColor" strokeWidth="2" strokeDasharray="4 3" />
        <path d="M6 18 L12 27 L18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function NodeShell({
  step,
  title,
  icon,
  active,
  done,
  children,
}: {
  step: string;
  title: string;
  icon: React.ReactNode;
  active: boolean;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`relative rounded-2xl border p-5 transition-colors md:p-6 ${
        active ? "border-primary/60 bg-white/[0.05]" : "border-white/10 bg-white/[0.02]"
      }`}
    >
      <div className="flex items-center gap-3">
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-full border ${
            active || done ? "border-primary/50 bg-primary/15 text-primary" : "border-white/15 text-white/40"
          }`}
        >
          {done ? <Check className="h-4 w-4" aria-hidden /> : icon}
        </span>
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.25em] text-white/40">Step {step}</p>
          <h3 className="text-lg font-black uppercase leading-tight">{title}</h3>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
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
  const restored = useRef(false);

  const unlimited = Boolean(me?.unlimited);
  const maxSeconds = me?.plan?.maxSecondsVideo ?? 15;
  const maxRes = me?.plan?.maxResolution ?? "720p";

  useEffect(() => {
    api<Me>("/api/me")
      .then((d) => {
        if (d.blocked) setAuthErr(`Account ${d.blocked.status}: ${d.blocked.reason}`);
        else setMe(d);
      })
      .catch((e) => setAuthErr(e instanceof Error ? e.message : "Sign in to use the studio"));
  }, []);

  // restore a saved project
  useEffect(() => {
    if (!projectId || restored.current) return;
    restored.current = true;
    api<{ projects: { id: string; title: string; niche: string; brief: string; scriptJson: string }[] }>(
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
      })
      .catch(() => undefined);
  }, [projectId]);

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
        body: JSON.stringify({ brief: enhanced || brief, niche, seconds: Math.min(60, maxSeconds) }),
      });
      setScript(d.script);
      setTitle(d.script.title);
      setTimeout(() => saveProject(d.script), 50);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Script writer failed");
    } finally {
      setWriting(false);
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
      <div className="mx-auto max-w-4xl px-4 py-10 md:py-14">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.25em] text-primary">AI Film Studio</p>
            <h1 className="mt-1 text-3xl font-black uppercase md:text-4xl">Watch the agent build your film</h1>
            <p className="mt-2 max-w-xl text-sm text-white/50">
              Brief the director. The agent enhances your prompt, writes the script, casts characters and
              pushes scenes to the render queue — every step connected, live.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${unlimited ? "border-primary/50 bg-primary/10 text-primary" : "border-white/15 text-white/60"}`}>
              {unlimited ? "Owner · Free ∞" : me.plan ? me.plan.maxSecondsVideo + "s · " + me.plan.maxResolution : "No plan"}
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

        {/* STEP 1 — BRIEF */}
        <div className="mt-8">
          <NodeShell step="1" title="The brief" icon={<Wand2 className="h-4 w-4" aria-hidden />} active={!stepsDone.brief} done={stepsDone.brief}>
            <p className="mb-3 text-sm text-white/50">Pick a niche — the whole pipeline tunes itself to it.</p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Niche">
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
                rows={3}
                placeholder="A boy discovers his drawing pen brings cartoons to life…"
                className="border-white/15 bg-white/5 text-white placeholder:text-white/30"
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
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
                <p className="text-[11px] font-black uppercase tracking-widest text-primary">Agent-enhanced prompt</p>
                <p className="mt-2 text-sm leading-relaxed text-white/85">{enhanced}</p>
                <button onClick={() => setBrief(enhanced)} className="mt-2 text-xs font-bold text-primary hover:underline">
                  Use as brief →
                </button>
              </div>
            )}
          </NodeShell>
        </div>

        <Connector active={Boolean(script)} />

        {/* STEP 2 — SCRIPT */}
        <NodeShell
          step="2"
          title={script ? script.title : "The script"}
          icon={<Film className="h-4 w-4" aria-hidden />}
          active={Boolean(script)}
          done={Boolean(script)}
        >
          {!script ? (
            <p className="text-sm text-white/40">
              The agent will split your brief into scenes with camera direction, cast the characters and write one line per shot.
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
                  <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
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
              <p className="text-xs text-white/40">
                {script.scenes.length} scenes · {totalSceneSeconds}s total
              </p>
            </div>
          )}
        </NodeShell>

        {/* STEP 3 — SCENES */}
        {script && (
          <>
            <Connector active />
            <NodeShell step="3" title="Scenes → render queue" icon={<Clapperboard className="h-4 w-4" aria-hidden />} active>
              <div className="space-y-3">
                {script.scenes.map((sc) => {
                  const r = render[sc.id];
                  return (
                    <div key={sc.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-black">
                          {sc.id} · {sc.title} <span className="text-white/40">({sc.seconds}s)</span>
                        </p>
                        {r && (
                          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-black uppercase ${
                            r.status === "done" ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400" :
                            r.status === "failed" ? "border-red-500/30 bg-red-500/15 text-red-400" :
                            "border-amber-500/30 bg-amber-500/15 text-amber-400"
                          }`}>
                            {r.status}{r.status === "queued" && r.etaDays ? ` · ~${r.etaDays}d` : ""}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm text-white/70">{sc.visual}</p>
                      {sc.line && <p className="mt-1 text-sm italic text-primary/90">“{sc.line}”</p>}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Button size="sm" onClick={() => submitScene(sc, maxRes, Boolean(me?.plan?.audio))} className="bg-primary font-bold text-white hover:bg-[#B91C1C]">
                          <Clapperboard className="h-3.5 w-3.5" aria-hidden /> Render scene
                        </Button>
                        {unlimited && (
                          <>
                            <Button size="sm" variant="outline" onClick={() => submitScene(sc, "1080p", true)} className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                              1080p + audio
                            </Button>
                          </>
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
          </>
        )}

        {/* LIVE RUN — the film simulator console */}
        {watch && (
          <div className="mt-6">
            <p className="mb-3 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-white/40">
              <Radio className="h-3.5 w-3.5 text-primary" aria-hidden /> Live run — the agent at work
            </p>
            <AgentStream requestId={watch} onClose={() => setWatch(null)} />
          </div>
        )}

        {/* STEP 4 — DELIVER */}
        {script && (
          <>
            <Connector active={Object.values(render).some((r) => r.status === "done")} />
            <NodeShell
              step="4"
              title="Delivery"
              icon={<Check className="h-4 w-4" aria-hidden />}
              active={Object.values(render).some((r) => r.status === "done")}
              done={Object.values(render).every((r) => r.status === "done") && Object.keys(render).length > 0}
            >
              <p className="text-sm text-white/50">
                Renders land here and in your <button onClick={() => go("/dashboard")} className="font-bold text-primary hover:underline">dashboard</button> — status polls live.
                {unlimited ? " Owner queue priority: first, always." : ""}
              </p>
              {activeScene && Object.keys(render).length === 0 && (
                <p className="mt-2 text-sm text-white/40">Start with {activeScene.id} — the establishing shot.</p>
              )}
            </NodeShell>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, ClipboardCheck, Film, Loader2, Search, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { api, type VideoRequest } from "@/lib/types";
import type { FilmPlan } from "@/lib/pipeline";
import { go } from "./hash";
import { SectionHead } from "./sections";

type SubmitResult = {
  request: VideoRequest;
  queuePosition: number;
  etaDays: number;
  fromCache: boolean;
  usage: { used: number; quota: number };
};

type StatusResult = {
  request: Pick<VideoRequest, "id" | "prompt" | "seconds" | "resolution" | "status" | "resultUrl" | "fromCache" | "createdAt">;
  queuePosition: number;
};

/** Public view: subscribers submit video requests and track them in the queue. */
export function RequestView() {
  const [email, setEmail] = useState("");
  const [prompt, setPrompt] = useState("");
  const [seconds, setSeconds] = useState(15);
  const [resolution, setResolution] = useState("720p");
  const [withAudio, setWithAudio] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  const [checkId, setCheckId] = useState("");
  const [checkEmail, setCheckEmail] = useState("");
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState<StatusResult | null>(null);

  /* film planner - one instruction -> full plan via the studio's specialist pipeline */
  const [showPlanner, setShowPlanner] = useState(false);
  const [planInstruction, setPlanInstruction] = useState("");
  const [planBusy, setPlanBusy] = useState(false);
  const [plan, setPlan] = useState<FilmPlan | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api<SubmitResult>("/api/requests", {
        method: "POST",
        body: JSON.stringify({ email, prompt, seconds, resolution, withAudio }),
      });
      setResult(res);
      toast.success(
        res.fromCache
          ? "Instant delivery from the render cache!"
          : `Queued - position ${res.queuePosition}. We render Elite first, then Pro, then Beginner.`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not submit request");
    } finally {
      setBusy(false);
    }
  }

  async function generatePlan(e: React.FormEvent) {
    e.preventDefault();
    if (planInstruction.trim().length < 12) return toast.error("Describe your film in a vivid sentence or two");
    setPlanBusy(true);
    setPlan(null);
    try {
      const res = await api<{ plan: FilmPlan }>("/api/pipeline/plan", {
        method: "POST",
        body: JSON.stringify({ instruction: planInstruction.trim() }),
      });
      setPlan(res.plan);
      toast.success(`"${res.plan.title}" is ready - ${res.plan.scenes.length} scenes, ~${res.plan.totalSeconds}s`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not draft the plan");
    } finally {
      setPlanBusy(false);
    }
  }

  function applyPlan() {
    if (!plan) return;
    setPrompt(plan.combinedPrompt);
    setSeconds(Math.min(60, Math.max(5, plan.totalSeconds)));
    setWithAudio(true);
    setResolution("1080p");
    toast.success("Plan loaded into the form - review it, then submit");
    document.getElementById("v-prompt")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function check(e: React.FormEvent) {
    e.preventDefault();
    if (!checkId.trim() || !checkEmail.trim()) return toast.error("Enter your request ID and email");
    setChecking(true);
    try {
      const res = await api<StatusResult>(
        `/api/requests/${encodeURIComponent(checkId.trim())}?email=${encodeURIComponent(checkEmail.trim())}`
      );
      setStatus(res);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request not found");
      setStatus(null);
    } finally {
      setChecking(false);
    }
  }

  const statusLabel: Record<string, string> = {
    queued: "In queue",
    rendering: "Rendering now",
    done: "Ready",
    failed: "Failed - the owner was notified",
    cancelled: "Cancelled",
  };

  return (
    <section className="py-12 md:py-20 bg-white min-h-[70vh]">
      <div className="mx-auto max-w-3xl px-4">
        <SectionHead kicker="AI Video Studio" title="Submit Your Video" dark={false} />

        {result ? (
          <div className="mt-10 border-2 border-primary p-6 space-y-4">
            {result.fromCache ? (
              <p className="inline-flex items-center gap-2 font-black text-lg">
                <CheckCircle2 className="h-5 w-5 text-primary" aria-hidden /> Delivered instantly from cache
              </p>
            ) : (
              <p className="inline-flex items-center gap-2 font-black text-lg">
                <Film className="h-5 w-5 text-primary" aria-hidden /> Queued - position {result.queuePosition}
              </p>
            )}
            <p className="text-sm text-neutral-600">
              {result.fromCache
                ? "An identical video was rendered before, so yours is ready right now."
                : `Estimated delivery: about ${result.etaDays} day${result.etaDays > 1 ? "s" : ""} at current demand (Elite first, then Pro, then Beginner).`}
            </p>
            <p className="text-sm text-neutral-600">
              Usage this period: <strong>{result.usage.used} / {result.usage.quota}</strong> videos.
            </p>
            <div className="bg-[#F7F7F7] border p-4">
              <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">Your request ID - keep it to check status</p>
              <p className="font-mono font-black break-all">{result.request.id}</p>
            </div>
            {result.request.resultUrl ? (
              <a
                href={result.request.resultUrl}
                download
                className="inline-flex items-center gap-2 font-bold text-primary hover:underline underline-offset-4"
              >
                <Film className="h-4 w-4" aria-hidden /> Download your video
              </a>
            ) : (
              <div>
                <Button onClick={() => setResult(null)} variant="outline" className="mr-3">
                  Submit another
                </Button>
                <Button onClick={() => setCheckId(result.request.id)}>Check status below</Button>
              </div>
            )}
          </div>
        ) : (
          <>
          {/* ---- film planner: one instruction -> structured plan ---- */}
          <div className="mt-10 border-2 border-dashed border-primary/50 bg-[#FFF8F8] p-5">
            <button
              type="button"
              onClick={() => setShowPlanner((v) => !v)}
              className="w-full flex items-center gap-3 text-left"
              aria-expanded={showPlanner}
            >
              <span className="h-10 w-10 shrink-0 grid place-items-center bg-primary text-white">
                <Sparkles className="h-5 w-5" aria-hidden />
              </span>
              <span className="flex-1">
                <span className="block font-black uppercase tracking-tight">Let the studio plan it for you</span>
                <span className="block text-sm text-neutral-600">One sentence in - a full 45-60s film plan out: script, scenes and shot prompts, drafted by the showrunner AI and checked by its script doctor.</span>
              </span>
              <span className="text-primary font-black text-xl" aria-hidden>{showPlanner ? "−" : "+"}</span>
            </button>

            {showPlanner && (
              <div className="mt-5 space-y-4">
                <form onSubmit={generatePlan} className="space-y-3">
                  <div className="space-y-2">
                    <Label htmlFor="v-plan">Your instruction - the whole idea, in plain words</Label>
                    <Textarea
                      id="v-plan" rows={3}
                      value={planInstruction} onChange={(e) => setPlanInstruction(e.target.value)}
                      placeholder="e.g. A 60-second cartoon ad for my shoe brand: a young runner in Lagos laces up, hits the streets, and the whole city starts dancing in our sneakers."
                    />
                  </div>
                  <Button
                    type="submit" disabled={planBusy}
                    className="bg-[var(--brand-black)] hover:bg-primary text-white font-bold"
                  >
                    {planBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Sparkles className="h-4 w-4" aria-hidden />}
                    {planBusy ? "The writers' room is working…" : "Plan my film"}
                  </Button>
                </form>

                {plan && (
                  <div className="border-2 border-primary bg-white p-4 space-y-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-widest text-primary">Film plan</p>
                      <h3 className="text-lg font-black uppercase tracking-tight">{plan.title}</h3>
                      <p className="text-sm text-neutral-600">{plan.logline}</p>
                      <p className="mt-1 text-xs text-neutral-500">Style: {plan.style} · {plan.totalSeconds}s total</p>
                    </div>
                    <ol className="space-y-2 text-sm">
                      {plan.scenes.map((s) => (
                        <li key={s.index} className="border-l-2 border-primary/40 pl-3">
                          <span className="font-black">{s.index}. {s.speaker}</span>
                          <span className="text-neutral-500"> · {s.seconds}s</span>
                          <p className="text-neutral-800">“{s.line}”</p>
                        </li>
                      ))}
                    </ol>
                    {plan.doctorFixes.length > 0 && (
                      <p className="text-xs text-neutral-500">
                        <strong className="text-primary">Script doctor:</strong> {plan.doctorFixes.join(" · ")}
                      </p>
                    )}
                    <Button onClick={applyPlan} className="w-full bg-primary hover:bg-[#B91C1C] text-white font-bold">
                      <ClipboardCheck className="h-4 w-4" aria-hidden /> Use this plan - load it into the form below
                    </Button>
                    <p className="text-[11px] text-neutral-500">
                      It fills the prompt, sets the length to ~{plan.totalSeconds}s with audio on - edit anything before submitting.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          <form onSubmit={submit} className="mt-10 space-y-5" aria-label="Video request form">
            <div className="space-y-2">
              <Label htmlFor="v-email">Subscriber email</Label>
              <Input
                id="v-email" type="email" required
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="The email you subscribed with"
              />
              <p className="text-xs text-muted-foreground">
                No subscription yet?{" "}
                <button type="button" onClick={() => go("#subscribe")} className="font-bold text-primary hover:underline underline-offset-4">
                  See plans & subscribe <ArrowRight className="h-3.5 w-3.5 inline align-[-2px]" aria-hidden />
                </button>
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="v-prompt">Describe your video</Label>
              <Textarea
                id="v-prompt" required rows={4}
                value={prompt} onChange={(e) => setPrompt(e.target.value)}
                placeholder="A slow-motion drone shot over a red desert at golden hour, cinematic, 4K mood…"
              />
            </div>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="v-seconds">Length (seconds)</Label>
                <select
                  id="v-seconds" value={seconds}
                  onChange={(e) => setSeconds(Number(e.target.value))}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {[5, 10, 15, 20, 30, 45, 60].map((n) => (
                    <option key={n} value={n}>{n}s</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="v-res">Resolution</Label>
                <select
                  id="v-res" value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="720p">720p HD</option>
                  <option value="1080p">1080p Full HD</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="v-audio">Audio</Label>
                <select
                  id="v-audio" value={withAudio ? "yes" : "no"}
                  onChange={(e) => setWithAudio(e.target.value === "yes")}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="no">No audio</option>
                  <option value="yes">With audio</option>
                </select>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Your plan&apos;s limits are applied automatically - if something is above your tier, you&apos;ll be told exactly what to do.
            </p>
            <Button
              type="submit" disabled={busy}
              className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
              {busy ? "Submitting…" : "Submit to the Queue"}
            </Button>
          </form>
          </>
        )}

        <div className="mt-14 border-t-2 border-neutral-100 pt-8">
          <h2 className="text-xl font-black uppercase tracking-tight inline-flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" aria-hidden /> Check a request
          </h2>
          <form onSubmit={check} className="mt-4 grid sm:grid-cols-[1fr_1fr_auto] gap-3 items-end">
            <div className="space-y-1.5">
              <Label htmlFor="c-id">Request ID</Label>
              <Input id="c-id" value={checkId} onChange={(e) => setCheckId(e.target.value)} placeholder="Paste your request ID" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="c-email">Email</Label>
              <Input id="c-email" type="email" value={checkEmail} onChange={(e) => setCheckEmail(e.target.value)} placeholder="you@example.com" />
            </div>
            <Button type="submit" disabled={checking} className="h-10 bg-[var(--brand-black)] hover:bg-primary text-white font-bold">
              {checking ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Check"}
            </Button>
          </form>

          {status && (
            <div className="mt-4 border-2 border-neutral-200 p-4 text-sm space-y-1">
              <p>
                <span className="font-black uppercase">{statusLabel[status.request.status] || status.request.status}</span>
                {status.queuePosition > 0 && status.request.status === "queued" ? ` - position ${status.queuePosition}` : ""}
              </p>
              <p className="text-neutral-500">
                {status.request.seconds}s · {status.request.resolution} · submitted{" "}
                {new Date(status.request.createdAt).toLocaleDateString()}
              </p>
              {status.request.status === "done" && status.request.resultUrl ? (
                <a href={status.request.resultUrl} download className="inline-flex items-center gap-2 font-bold text-primary hover:underline">
                  <Film className="h-4 w-4" aria-hidden /> Download your video
                </a>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

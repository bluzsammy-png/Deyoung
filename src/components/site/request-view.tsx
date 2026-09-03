"use client";

import { useState } from "react";
import { CheckCircle2, Film, Loader2, Search, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { api, type VideoRequest } from "@/lib/types";
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
          : `Queued — position ${res.queuePosition}. We render Elite first, then Pro, then Beginner.`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not submit request");
    } finally {
      setBusy(false);
    }
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
    failed: "Failed — the owner was notified",
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
                <Film className="h-5 w-5 text-primary" aria-hidden /> Queued — position {result.queuePosition}
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
              <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">Your request ID — keep it to check status</p>
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
                <button type="button" onClick={() => go("#plans")} className="font-bold text-primary hover:underline underline-offset-4">
                  See plans →
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
              Your plan&apos;s limits are applied automatically — if something is above your tier, you&apos;ll be told exactly what to do.
            </p>
            <Button
              type="submit" disabled={busy}
              className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
              {busy ? "Submitting…" : "Submit to the Queue"}
            </Button>
          </form>
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
                {status.queuePosition > 0 && status.request.status === "queued" ? ` — position ${status.queuePosition}` : ""}
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

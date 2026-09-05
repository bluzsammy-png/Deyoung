"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Clapperboard, Film, Loader2, Users, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { api, money, type Plan, type Subscription, type VideoRequest } from "@/lib/types";
import { StatusBadge } from "./admin-app";

/* ================= Plans ================= */

function featuresToText(json: string): string {
  try {
    const arr = JSON.parse(json) as { label: string; included: boolean }[];
    return arr.map((f) => (f.included ? f.label : `- ${f.label}`)).join("\n");
  } catch {
    return "";
  }
}

function textToFeatures(text: string): string {
  const arr = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => (l.startsWith("-") ? { label: l.slice(1).trim(), included: false } : { label: l, included: true }));
  return JSON.stringify(arr);
}

type PlanDraft = Plan & { featuresText: string };

export function AdminPlans() {
  const [drafts, setDrafts] = useState<PlanDraft[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ plans: Plan[] }>("/api/plans")
      .then(({ plans }) => setDrafts(plans.map((p) => ({ ...p, featuresText: featuresToText(p.featuresJson) }))))
      .catch(() => toast.error("Could not load plans"));
  }, []);

  function patch(code: string, fields: Partial<PlanDraft>) {
    setDrafts((ds) => (ds ?? []).map((d) => (d.code === code ? { ...d, ...fields } : d)));
  }

  async function save() {
    if (!drafts) return;
    setBusy(true);
    try {
      const plans = drafts.map((d) => ({
        code: d.code,
        name: d.name,
        blurb: d.blurb,
        priceMonthly: d.priceMonthly,
        currency: d.currency,
        maxVideosMonth: d.maxVideosMonth,
        maxSecondsVideo: d.maxSecondsVideo,
        maxResolution: d.maxResolution,
        watermark: d.watermark,
        concurrentJobs: d.concurrentJobs,
        queuePriority: d.queuePriority,
        commercial: d.commercial,
        audio: d.audio,
        featuresJson: textToFeatures(d.featuresText),
        active: d.active,
        sortOrder: d.sortOrder,
      }));
      const res = await api<{ plans: Plan[] }>("/api/plans", {
        method: "PUT",
        body: JSON.stringify({ plans }),
      });
      setDrafts(res.plans.map((p) => ({ ...p, featuresText: featuresToText(p.featuresJson) })));
      toast.success("Plans saved - the public pricing page is updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save plans");
    } finally {
      setBusy(false);
    }
  }

  if (!drafts) return <p className="text-muted-foreground p-6">Loading plans…</p>;

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Every limit is yours to set - prices, video counts, seconds per video, resolution, watermark, queue priority.
        Lines starting with &quot;-&quot; in the feature list show as excluded on the pricing card.
      </p>
      {drafts.map((d) => (
        <div key={d.code} className="bg-white border-2 border-neutral-200 p-5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h3 className="font-black uppercase tracking-tight inline-flex items-center gap-2">
              <Clapperboard className="h-5 w-5 text-primary" aria-hidden /> {d.code}
            </h3>
            <label className="inline-flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={d.active}
                onChange={(e) => patch(d.code, { active: e.target.checked })}
                aria-label={`${d.code} visible on site`}
              />
              Visible on site
            </label>
          </div>
          <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor={`p-name-${d.code}`}>Display name</Label>
              <Input id={`p-name-${d.code}`} value={d.name} onChange={(e) => patch(d.code, { name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-price-${d.code}`}>Price / month</Label>
              <Input
                id={`p-price-${d.code}`} type="number" min={0} step="0.01"
                value={d.priceMonthly}
                onChange={(e) => patch(d.code, { priceMonthly: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-videos-${d.code}`}>Videos / month</Label>
              <Input
                id={`p-videos-${d.code}`} type="number" min={1}
                value={d.maxVideosMonth}
                onChange={(e) => patch(d.code, { maxVideosMonth: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-secs-${d.code}`}>Max seconds / video</Label>
              <Input
                id={`p-secs-${d.code}`} type="number" min={5} max={600}
                value={d.maxSecondsVideo}
                onChange={(e) => patch(d.code, { maxSecondsVideo: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-res-${d.code}`}>Max resolution</Label>
              <select
                id={`p-res-${d.code}`} value={d.maxResolution}
                onChange={(e) => patch(d.code, { maxResolution: e.target.value })}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="480p">480p</option>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-conc-${d.code}`}>Concurrent renders</Label>
              <Input
                id={`p-conc-${d.code}`} type="number" min={1} max={10}
                value={d.concurrentJobs}
                onChange={(e) => patch(d.code, { concurrentJobs: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-prio-${d.code}`}>Queue priority (0-5)</Label>
              <Input
                id={`p-prio-${d.code}`} type="number" min={0} max={5}
                value={d.queuePriority}
                onChange={(e) => patch(d.code, { queuePriority: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`p-cur-${d.code}`}>Currency</Label>
              <Input id={`p-cur-${d.code}`} value={d.currency} onChange={(e) => patch(d.code, { currency: e.target.value.toUpperCase() })} />
            </div>
          </div>
          <div className="mt-4 grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor={`p-blurb-${d.code}`}>Blurb</Label>
              <Input id={`p-blurb-${d.code}`} value={d.blurb} onChange={(e) => patch(d.code, { blurb: e.target.value })} />
            </div>
            <div className="flex items-center gap-5 pt-6 flex-wrap">
              <label className="inline-flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" checked={!d.watermark} onChange={(e) => patch(d.code, { watermark: !e.target.checked })} />
                No watermark
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" checked={d.audio} onChange={(e) => patch(d.code, { audio: e.target.checked })} />
                Audio
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" checked={d.commercial} onChange={(e) => patch(d.code, { commercial: e.target.checked })} />
                Commercial license
              </label>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            <Label htmlFor={`p-feat-${d.code}`}>Feature list (one per line, prefix &quot;-&quot; = not included)</Label>
            <Textarea
              id={`p-feat-${d.code}`} rows={5}
              value={d.featuresText}
              onChange={(e) => patch(d.code, { featuresText: e.target.value })}
            />
          </div>
        </div>
      ))}
      <Button onClick={save} disabled={busy} className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null} Save all plans
      </Button>
    </div>
  );
}

/* ================= Subscribers ================= */

export function AdminSubscribers() {
  const [subs, setSubs] = useState<Subscription[] | null>(null);
  const [months, setMonths] = useState<Record<string, number>>({});

  const load = useCallback(() => {
    api<{ subscriptions: Subscription[] }>("/api/subscriptions")
      .then(({ subscriptions }) => setSubs(subscriptions))
      .catch(() => toast.error("Could not load subscribers"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id: string, action: string, extra: Record<string, unknown> = {}) {
    try {
      await api(`/api/subscriptions/${id}`, { method: "PATCH", body: JSON.stringify({ action, ...extra }) });
      toast.success(`Subscription ${action}d`);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this subscriber and all their video requests?")) return;
    try {
      await api(`/api/subscriptions/${id}`, { method: "DELETE" });
      toast.success("Deleted");
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  if (!subs) return <p className="text-muted-foreground p-6">Loading subscribers…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        <Users className="h-4 w-4 inline text-primary" aria-hidden /> Manual payments: once the money lands, press
        <strong> Activate</strong> - that starts their monthly period and unlocks the video queue.
      </p>
      {subs.length === 0 ? (
        <p className="p-6 bg-white border-2 border-neutral-200 text-sm text-muted-foreground">
          No subscribers yet - share your plans page to get the first one.
        </p>
      ) : (
        subs.map((s) => (
          <div key={s.id} className="bg-white border-2 border-neutral-200 p-5">
            <div className="flex items-center gap-3 flex-wrap">
              <StatusBadge status={s.status} />
              <span className="font-black">{s.name}</span>
              <span className="text-sm text-muted-foreground">{s.email}</span>
              {s.phone ? <span className="text-sm text-muted-foreground">· {s.phone}</span> : null}
              <span className="ml-auto font-black">{money(s.pricePaid, s.currency)}<span className="text-xs font-semibold text-muted-foreground"> /mo</span></span>
            </div>
            <div className="mt-2 flex items-center gap-3 flex-wrap text-sm text-muted-foreground">
              <span className="uppercase font-bold text-primary">{s.planCode}</span>
              {s.periodEnd ? <span>active until {new Date(s.periodEnd).toLocaleDateString()}</span> : null}
              <span>via {s.provider}</span>
              {s.paymentRef ? <span className="font-mono text-xs">ref {s.paymentRef}</span> : null}
            </div>
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <Input
                type="number" min={1} max={24} aria-label={`Months for ${s.email}`}
                className="w-24 h-9"
                value={months[s.id] ?? 1}
                onChange={(e) => setMonths({ ...months, [s.id]: Number(e.target.value) })}
              />
              <span className="text-xs text-muted-foreground">month(s)</span>
              <Button size="sm" onClick={() => act(s.id, "activate", { months: months[s.id] ?? 1 })} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
                Activate
              </Button>
              {s.status === "active" ? (
                <Button size="sm" variant="outline" onClick={() => act(s.id, "cancel")}>Cancel sub</Button>
              ) : (
                <Button size="sm" variant="outline" onClick={() => act(s.id, "reactivate")}>Set pending</Button>
              )}
              <Button size="sm" variant="outline" onClick={() => remove(s.id)} className="text-primary border-primary/40 hover:bg-primary hover:text-white">
                Delete
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

/* ================= Requests (render queue) ================= */

export function AdminRequests() {
  const [requests, setRequests] = useState<VideoRequest[] | null>(null);
  const [gpu, setGpu] = useState<Record<string, string>>({});
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const load = useCallback(() => {
    api<{ requests: VideoRequest[] }>("/api/requests")
      .then(({ requests }) => setRequests(requests))
      .catch(() => toast.error("Could not load the queue"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id: string, action: string, extra: Record<string, unknown> = {}) {
    try {
      await api(`/api/requests/${id}`, { method: "PATCH", body: JSON.stringify({ action, ...extra }) });
      toast.success(`Request ${action === "deliver" ? "delivered" : action + "ed"}`);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    }
  }

  async function uploadAndDeliver(id: string) {
    const input = fileRefs.current[id];
    const file = input?.files?.[0];
    if (!file) return toast.error("Choose the rendered video file first");
    setBusyUpload(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api<{ url: string }>("/api/upload", { method: "POST", body: fd });
      await act(id, "deliver", { resultUrl: res.url, gpuMinutes: parseFloat(gpu[id] || "0") });
      if (input) input.value = "";
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusyUpload(false);
    }
  }

  const [busyUpload, setBusyUpload] = useState(false);

  if (!requests) return <p className="text-muted-foreground p-6">Loading the queue…</p>;

  const order = { rendering: 0, queued: 1, done: 2, failed: 3, cancelled: 4 } as Record<string, number>;
  const sorted = [...requests].sort(
    (a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9) || b.queuePriority - a.queuePriority || a.createdAt.localeCompare(b.createdAt)
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        <Film className="h-4 w-4 inline text-primary" aria-hidden /> The render queue: Elite first, then Pro, then Beginner, oldest first
        within a tier. Start a render, then upload the finished video to deliver it - the subscriber sees it instantly at their status link.
      </p>
      {sorted.length === 0 ? (
        <p className="p-6 bg-white border-2 border-neutral-200 text-sm text-muted-foreground">
          The queue is empty. Once subscribers submit prompts, they appear here.
        </p>
      ) : (
        sorted.map((r) => (
          <div key={r.id} className="bg-white border-2 border-neutral-200 p-5">
            <div className="flex items-center gap-3 flex-wrap">
              <StatusBadge status={r.status === "done" ? "paid" : r.status === "rendering" ? "confirmed" : r.status === "queued" ? "pending" : "cancelled"} />
              {r.fromCache ? <span className="text-[11px] font-black uppercase px-2 py-1 bg-neutral-900 text-white">cache hit</span> : null}
              <span className="font-mono text-xs text-muted-foreground">{r.id.slice(0, 10)}</span>
              <span className="text-sm text-muted-foreground">{r.email}</span>
              <span className="ml-auto text-sm font-bold">{r.seconds}s · {r.resolution}{r.withAudio ? " · audio" : ""}{r.watermark ? " · watermark" : ""}</span>
            </div>
            <p className="mt-2 text-sm text-neutral-700 leading-relaxed border-l-4 border-neutral-100 pl-3">
              {r.prompt.length > 220 ? `${r.prompt.slice(0, 220)}…` : r.prompt}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              submitted {new Date(r.createdAt).toLocaleString()}
              {r.status === "done" && r.resultUrl ? (
                <>
                  {" "}· delivered - <a href={r.resultUrl} className="text-primary font-bold hover:underline" target="_blank" rel="noopener noreferrer">view file</a>
                  {r.gpuMinutes ? ` · ${r.gpuMinutes} GPU-min` : ""}
                </>
              ) : null}
            </p>
            {["queued", "rendering"].includes(r.status) && (
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                {r.status === "queued" && (
                  <Button size="sm" onClick={() => act(r.id, "start")} className="bg-[var(--brand-black)] hover:bg-primary text-white font-bold">
                    Start render
                  </Button>
                )}
                <input
                  ref={(el) => { fileRefs.current[r.id] = el; }}
                  type="file" accept="video/mp4,video/webm,video/quicktime"
                  aria-label={`Result video for ${r.id}`}
                  className="text-xs"
                />
                <Input
                  type="number" min={0} step="0.1" placeholder="GPU-min used"
                  aria-label={`GPU minutes for ${r.id}`}
                  className="w-32 h-9"
                  value={gpu[r.id] ?? ""}
                  onChange={(e) => setGpu({ ...gpu, [r.id]: e.target.value })}
                />
                <Button size="sm" disabled={busyUpload} onClick={() => uploadAndDeliver(r.id)} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
                  {busyUpload ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Wallet className="h-4 w-4" aria-hidden />} Deliver
                </Button>
                <Button size="sm" variant="outline" onClick={() => act(r.id, "cancel")}>Cancel</Button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

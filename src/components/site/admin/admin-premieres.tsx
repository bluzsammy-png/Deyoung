"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, ExternalLink, Loader2, Popcorn, Star, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api } from "@/lib/types";

/**
 * W2.2 — Admin Premieres tab: curate the public Premiere Wall.
 *  1. Pending user requests — approve (publishes + flips the render asset
 *     public) or reject (nothing is ever exposed).
 *  2. Put a delivered render on the wall — any done render with a result asset
 *     that is not premiered yet.
 *  3. On the wall — edit copy, feature, unpublish/republish, delete. Every
 *     status change keeps the underlying asset's public flag honest.
 */

type AdminPremiere = {
  id: string;
  title: string;
  logline: string;
  category: string;
  durationSec: number;
  videoUrl: string;
  posterUrl: string;
  featured: boolean;
  status: string;
  source: string;
  requestedBy: string;
  postedAt: string;
  videoSrc: string;
  requestId: string | null;
  renderPrompt: string;
  renderEmail: string;
};

type Eligible = {
  id: string;
  prompt: string;
  email: string;
  seconds: number;
  resolution: string;
  resultAssetId: string | null;
  createdAt: string;
};

const CATEGORIES = ["ai-film", "style-lab", "studio", "commercial"];

function fmtDuration(sec: number): string {
  if (!sec || sec <= 0) return "";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function AdminPremieres() {
  const [premieres, setPremieres] = useState<AdminPremiere[] | null>(null);
  const [eligible, setEligible] = useState<Eligible[]>([]);
  const [busy, setBusy] = useState(false);
  const [creatingFrom, setCreatingFrom] = useState<Eligible | null>(null);
  const [draft, setDraft] = useState({ title: "", logline: "", category: "ai-film", posterUrl: "", featured: false });

  const load = useCallback(() => {
    api<{ premieres: AdminPremiere[]; eligible: Eligible[] }>("/api/admin/premieres")
      .then((d) => {
        setPremieres(d.premieres);
        setEligible(d.eligible);
      })
      .catch(() => toast.error("Could not load premieres"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function act(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    try {
      await fn();
      toast.success(done);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const pending = (premieres ?? []).filter((p) => p.status === "pending");
  const wall = (premieres ?? []).filter((p) => p.status !== "pending");

  return (
    <div className="space-y-8">
      {/* 1 — pending user requests */}
      <section className="rounded-2xl border border-neutral-200 bg-white p-6">
        <h2 className="flex items-center gap-2 text-sm font-black uppercase tracking-widest text-neutral-500">
          <Popcorn className="h-4 w-4 text-primary" aria-hidden /> Premiere requests ({pending.length})
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Users asked for their delivered films to screen on the public wall. Approving makes the video publicly watchable.
        </p>
        {pending.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">No requests waiting.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {pending.map((p) => (
              <div key={p.id} className="rounded-xl border border-neutral-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-bold">{p.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {p.requestedBy} · {p.category} · {fmtDuration(p.durationSec) || `${p.durationSec}s`} ·{" "}
                      {new Date(p.postedAt).toLocaleDateString()}
                    </p>
                    {p.logline && <p className="mt-1 text-sm text-neutral-600">{p.logline}</p>}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <a
                      href={p.videoSrc}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline"
                    >
                      Preview <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={() => act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify({ status: "published" }) }), "Premiere is live on the wall")}
                      className="bg-emerald-600 font-bold text-white hover:bg-emerald-700"
                    >
                      <Check className="h-4 w-4" aria-hidden /> Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={() => act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify({ status: "rejected" }) }), "Request rejected")}
                    >
                      <X className="h-4 w-4" aria-hidden /> Reject
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 2 — premiere a delivered render */}
      <section className="rounded-2xl border border-neutral-200 bg-white p-6">
        <h2 className="text-sm font-black uppercase tracking-widest text-neutral-500">Delivered renders ready to premiere ({eligible.length})</h2>
        <p className="mt-1 text-sm text-muted-foreground">Finished videos from the queue that are not on the wall yet.</p>
        {eligible.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">Nothing waiting — new deliveries appear here automatically.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {eligible.map((r) => (
              <div key={r.id} className="rounded-xl border border-neutral-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="line-clamp-2 text-sm font-semibold">{r.prompt}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {r.email} · {r.seconds}s · {r.resolution} · {new Date(r.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => {
                      setCreatingFrom(r);
                      setDraft({ title: r.prompt.slice(0, 80), logline: "", category: "ai-film", posterUrl: "", featured: false });
                    }}
                    variant={creatingFrom?.id === r.id ? "outline" : "default"}
                    className="shrink-0 font-bold"
                  >
                    <Star className="h-4 w-4" aria-hidden /> Premiere
                  </Button>
                </div>
                {creatingFrom?.id === r.id && (
                  <div className="mt-4 space-y-3 rounded-xl bg-neutral-50 p-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="prem-title">Title</Label>
                      <Input id="prem-title" value={draft.title} maxLength={120} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="prem-logline">Logline</Label>
                      <Input id="prem-logline" value={draft.logline} maxLength={280} onChange={(e) => setDraft({ ...draft, logline: e.target.value })} placeholder="One line that sells the film" />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label htmlFor="prem-cat">Category</Label>
                        <select
                          id="prem-cat"
                          value={draft.category}
                          onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                          className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
                        >
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="prem-poster">Poster URL (optional)</Label>
                        <Input id="prem-poster" value={draft.posterUrl} onChange={(e) => setDraft({ ...draft, posterUrl: e.target.value })} placeholder="/img/… or https://…" />
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-sm font-semibold">
                      <input
                        type="checkbox"
                        checked={draft.featured}
                        onChange={(e) => setDraft({ ...draft, featured: e.target.checked })}
                        className="h-4 w-4 accent-[var(--brand-red)]"
                      />
                      Feature on the wall (pinned first)
                    </label>
                    <div className="flex items-center gap-2">
                      <Button
                        disabled={busy || draft.title.trim().length === 0}
                        onClick={() =>
                          act(
                            () =>
                              api("/api/admin/premieres", {
                                method: "POST",
                                body: JSON.stringify({ requestId: r.id, ...draft }),
                              }),
                            "Premiere published to the wall"
                          ).then(() => setCreatingFrom(null))
                        }
                        className="bg-primary font-bold text-white hover:bg-[#B91C1C]"
                      >
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Check className="h-4 w-4" aria-hidden />} Publish
                      </Button>
                      <Button variant="outline" onClick={() => setCreatingFrom(null)}>Cancel</Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 3 — on the wall */}
      <section className="rounded-2xl border border-neutral-200 bg-white p-6">
        <h2 className="text-sm font-black uppercase tracking-widest text-neutral-500">On the wall ({wall.length})</h2>
        {wall.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">The wall is empty — premiere a film above.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {wall.map((p) => (
              <WallRow key={p.id} p={p} busy={busy} act={act} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function WallRow({
  p,
  busy,
  act,
}: {
  p: AdminPremiere;
  busy: boolean;
  act: (fn: () => Promise<unknown>, done: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: p.title, logline: p.logline, category: p.category });

  return (
    <div className={`rounded-xl border p-4 ${p.status === "rejected" ? "border-neutral-200 bg-neutral-50 opacity-70" : "border-neutral-200"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 font-bold">
            {p.featured && <Star className="h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden />}
            <span className="line-clamp-1">{p.title}</span>
            <span className="rounded-full border border-neutral-200 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-neutral-500">
              {p.status}
            </span>
            <span className="rounded-full border border-neutral-200 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-neutral-500">
              {p.source}
            </span>
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {p.category} · {fmtDuration(p.durationSec) || `${p.durationSec}s`} · {p.renderEmail || p.requestedBy} ·{" "}
            {new Date(p.postedAt).toLocaleDateString()}
          </p>
          {p.logline && !editing && <p className="mt-1 line-clamp-1 text-sm text-neutral-600">{p.logline}</p>}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <a href={p.videoSrc} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline">
            Watch <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
          <Button size="sm" variant="outline" disabled={busy} onClick={() => setEditing((v) => !v)}>
            {editing ? "Close" : "Edit"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify({ featured: !p.featured }) }), p.featured ? "Unfeatured" : "Featured on the wall")}
          >
            <Star className="h-4 w-4" aria-hidden /> {p.featured ? "Unfeature" : "Feature"}
          </Button>
          {p.status === "published" ? (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify({ status: "rejected" }) }), "Taken off the wall — video is private again")}
            >
              Unpublish
            </Button>
          ) : (
            <Button
              size="sm"
              disabled={busy}
              onClick={() => act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify({ status: "published" }) }), "Back on the wall")}
              className="bg-emerald-600 font-bold text-white hover:bg-emerald-700"
            >
              Republish
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => {
              if (!window.confirm(`Remove "${p.title}" from the wall for good?`)) return;
              act(() => api(`/api/admin/premieres/${p.id}`, { method: "DELETE" }), "Premiere removed");
            }}
            className="border-red-200 text-red-600 hover:bg-red-50"
            aria-label={`Delete premiere ${p.title}`}
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>
      {editing && (
        <div className="mt-4 grid gap-3 rounded-xl bg-neutral-50 p-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor={`edit-title-${p.id}`}>Title</Label>
            <Input id={`edit-title-${p.id}`} value={form.title} maxLength={120} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={`edit-cat-${p.id}`}>Category</Label>
            <select
              id={`edit-cat-${p.id}`}
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor={`edit-logline-${p.id}`}>Logline</Label>
            <Input id={`edit-logline-${p.id}`} value={form.logline} maxLength={280} onChange={(e) => setForm({ ...form, logline: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Button
              disabled={busy || form.title.trim().length === 0}
              onClick={async () => {
                await act(() => api(`/api/admin/premieres/${p.id}`, { method: "PATCH", body: JSON.stringify(form) }), "Premiere updated");
                setEditing(false);
              }}
              className="bg-primary font-bold text-white hover:bg-[#B91C1C]"
            >
              Save changes
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

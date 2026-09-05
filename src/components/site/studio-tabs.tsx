"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Check, Download, Loader2, Send, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type StudioRequest, type StudioUser, type SupportMsg } from "@/lib/types";
import { go } from "./hash";
import { VoiceLicenseList, useLicensedVoices } from "./voice-clone";

/* ---------------- My Videos ---------------- */

export function VideosTab({ requests }: { requests: StudioRequest[] }) {
  const done = requests.filter((r) => r.status === "done" && r.resultUrl);
  if (done.length === 0) {
    return (
      <EmptyState
        title="No finished videos yet"
        body="Submit a script from the Create tab - finished renders land here automatically, ready to watch and download."
      />
    );
  }
  return (
    <div className="grid md:grid-cols-2 gap-4">
      {done.map((r) => (
        <div key={r.id} className="border border-white/15 bg-white/5 overflow-hidden">
          <div className="relative aspect-video bg-black">
            <video
              src={r.resultUrl}
              controls
              playsInline
              preload="metadata"
              className="w-full h-full object-contain"
              aria-label={`Finished video: ${r.prompt.slice(0, 60)}`}
            />
            {r.fromCache && (
              <span className="absolute top-2 left-2 bg-white/90 text-black text-[10px] font-black uppercase tracking-widest px-2 py-1">
                cache - instant
              </span>
            )}
          </div>
          <div className="p-4">
            <p className="text-sm font-bold line-clamp-2">{r.prompt}</p>
            <p className="mt-1 text-xs text-white/50 uppercase tracking-widest">
              {r.model} · {r.seconds}s · {r.resolution}
            </p>
            <div className="mt-3 flex gap-2">
              <a href={r.resultUrl} download className="flex-1">
                <Button variant="outline" className="w-full border-white/30 text-white hover:bg-white hover:text-black">
                  <Download className="h-4 w-4" aria-hidden /> Download
                </Button>
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---------------- Profile ---------------- */

export function ProfileTab({
  user, planName, used, max, onUserUpdated, onSignOut,
}: {
  user: StudioUser;
  planName: string | null;
  used: number;
  max: number | null;
  onUserUpdated: (u: StudioUser) => void;
  onSignOut: () => void;
}) {
  const [form, setForm] = useState({ name: user.name, phone: (user as { phone?: string }).phone || "" });
  const [pw, setPw] = useState({ currentPassword: "", newPassword: "" });
  const [saved, setSaved] = useState(false);
  const [pwMsg, setPwMsg] = useState("");
  const [uploading, setUploading] = useState(false);
  const { voices, reload: reloadVoices } = useLicensedVoices();

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await api<{ user: StudioUser }>("/api/user/me", { method: "PATCH", body: JSON.stringify(form) });
      onUserUpdated(res.user);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch { /* handled by toast-free inline state */ }
  }

  async function changePw(e: React.FormEvent) {
    e.preventDefault();
    setPwMsg("");
    try {
      await api("/api/user/password", { method: "POST", body: JSON.stringify(pw) });
      setPwMsg("Password changed.");
      setPw({ currentPassword: "", newPassword: "" });
    } catch (err) {
      setPwMsg(err instanceof Error ? err.message : "Could not change password");
    }
  }

  async function uploadAvatar(file: File) {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("kind", "avatar");
      const res = await api<{ url: string }>("/api/studio/upload", { method: "POST", body: fd });
      const updated = await api<{ user: StudioUser }>("/api/user/me", {
        method: "PATCH",
        body: JSON.stringify({ avatarUrl: res.url }),
      });
      onUserUpdated(updated.user);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="border border-white/15 bg-white/5 p-5">
          <h3 className="font-black uppercase tracking-tight">Your profile</h3>
          <div className="mt-4 flex items-center gap-4">
            <div className="relative h-16 w-16 overflow-hidden border-2 border-primary bg-black">
              {user.avatarUrl ? (
                <Image src={user.avatarUrl} alt="Your avatar" fill sizes="64px" className="object-cover" />
              ) : (
                <span className="absolute inset-0 grid place-items-center text-xl font-black text-primary">
                  {(user.name || user.email).slice(0, 1).toUpperCase()}
                </span>
              )}
            </div>
            <label className="text-xs font-bold uppercase tracking-widest text-white/60 hover:text-white cursor-pointer border border-white/25 px-3 py-2 inline-flex items-center gap-2">
              {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Upload className="h-3.5 w-3.5" aria-hidden />}
              {uploading ? "Uploading…" : "Change avatar"}
              <input
                type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadAvatar(f); }}
              />
            </label>
          </div>
          <form onSubmit={saveProfile} className="mt-4 space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="p-name" className="text-white/70 text-xs uppercase tracking-widest">Name</Label>
              <Input id="p-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="bg-white/5 border-white/20 text-white focus-visible:ring-primary" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="p-phone" className="text-white/70 text-xs uppercase tracking-widest">Phone (WhatsApp)</Label>
              <Input id="p-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+234…"
                className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-white/70 text-xs uppercase tracking-widest">Email</Label>
              <p className="text-sm text-white/50">{user.email} <span className="text-[10px] uppercase">(can&apos;t be changed)</span></p>
            </div>
            <Button type="submit" className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
              {saved ? <><Check className="h-4 w-4" aria-hidden /> Saved</> : "Save profile"}
            </Button>
          </form>
        </div>

        <div className="border border-white/15 bg-white/5 p-5">
          <h3 className="font-black uppercase tracking-tight">Change password</h3>
          <form onSubmit={changePw} className="mt-4 space-y-3">
            <Input type="password" required placeholder="Current password" value={pw.currentPassword}
              onChange={(e) => setPw({ ...pw, currentPassword: e.target.value })}
              autoComplete="current-password"
              className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
            <Input type="password" required placeholder="New password (min 8 chars)" value={pw.newPassword}
              onChange={(e) => setPw({ ...pw, newPassword: e.target.value })}
              autoComplete="new-password"
              className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
            {pwMsg && <p className="text-sm font-semibold text-white/80">{pwMsg}</p>}
            <Button type="submit" variant="outline" className="border-white/30 text-white hover:bg-white hover:text-black font-bold">
              Update password
            </Button>
          </form>
        </div>
      </div>

      <div className="space-y-6">
        <div className="border border-primary/60 bg-primary/10 p-5">
          <h3 className="font-black uppercase tracking-tight">Your plan</h3>
          {planName ? (
            <>
              <p className="mt-2 text-2xl font-black">{planName}</p>
              <p className="mt-1 text-sm text-white/70">
                {used} of {max} videos used this period. Your rate stays locked while you stay subscribed.
              </p>
              <Button onClick={() => go("#subscribe")} variant="outline" className="mt-4 border-white/30 text-white hover:bg-white hover:text-black font-bold">
                Upgrade plan
              </Button>
            </>
          ) : (
            <>
              <p className="mt-2 text-sm text-white/70">
                No active subscription - rendering is locked until you pick a plan. Your rate stays locked while you stay subscribed.
              </p>
              <Button onClick={() => go("#subscribe")} className="mt-4 bg-primary hover:bg-[#B91C1C] text-white font-bold">
                See plans & subscribe
              </Button>
            </>
          )}
        </div>

        <div className="border border-white/15 bg-white/5 p-5">
          <h3 className="font-black uppercase tracking-tight">Voice licenses</h3>
          <VoiceLicenseList voices={voices} onRevoked={reloadVoices} />
        </div>

        <div className="border border-white/15 bg-white/5 p-5">
          <h3 className="font-black uppercase tracking-tight">Session</h3>
          <p className="mt-2 text-sm text-white/60">Signed in as {user.email}.</p>
          <Button onClick={onSignOut} variant="outline" className="mt-4 border-primary text-primary hover:bg-primary hover:text-white font-bold">
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Support chat ---------------- */

export function SupportTab({ user }: { user: StudioUser }) {
  const [messages, setMessages] = useState<SupportMsg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api<{ messages: SupportMsg[] }>("/api/support/messages")
        .then((r) => { if (alive) setMessages(r.messages); })
        .catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    setSending(true);
    setText("");
    try {
      await api("/api/support/messages", { method: "POST", body: JSON.stringify({ body }) });
      const r = await api<{ messages: SupportMsg[] }>("/api/support/messages");
      setMessages(r.messages);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="border border-white/15 bg-white/5">
        <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
          <span className="h-2 w-2 bg-primary rounded-full animate-pulse" aria-hidden />
          <p className="text-xs font-black uppercase tracking-widest">Live support - replies from the DeYoung team</p>
        </div>
        <div className="h-[380px] overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-white/50 leading-relaxed">
              Hi {user.name.split(" ")[0] || "there"} - ask anything about your renders, your plan or a booking. We reply right here.
            </p>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.fromUser ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed ${
                  m.fromUser ? "bg-primary text-white" : "bg-white/10 text-white border border-white/10"
                }`}
              >
                {m.body}
                <span className={`block mt-1 text-[10px] ${m.fromUser ? "text-white/70" : "text-white/40"}`}>
                  {new Date(m.createdAt).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form onSubmit={send} className="p-3 border-t border-white/10 flex gap-2">
          <Input
            value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Type your message…"
            className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
            aria-label="Support message"
          />
          <Button type="submit" disabled={sending || !text.trim()} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
            <Send className="h-4 w-4" aria-hidden />
          </Button>
        </form>
      </div>
    </div>
  );
}

/* ---------------- shared ---------------- */

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-dashed border-white/20 p-10 text-center">
      <p className="font-black uppercase tracking-tight">{title}</p>
      <p className="mt-2 text-sm text-white/60 max-w-md mx-auto leading-relaxed">{body}</p>
    </div>
  );
}

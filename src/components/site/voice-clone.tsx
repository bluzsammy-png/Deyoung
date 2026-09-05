"use client";

import { useCallback, useEffect, useState } from "react";
import { BadgeCheck, Loader2, Mic, ShieldCheck, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type LicensedVoice, type StudioUser } from "@/lib/types";

/**
 * Voice-clone licensing UI. Consent-first: a voiceprint only exists here
 * together with its license evidence (sample + recorded consent statement,
 * plus written permission for third-party voices). Nothing is cloned from
 * random recordings - that's the whole point of the license.
 */

export const CONSENT_PHRASE = (name: string) =>
  `I am ${name || "[your full name]"}, and I am the owner of this voice. I authorize DeYoung to create an AI clone of my voice for use on my own DeYoung account, under the DeYoung Voice Clone License. I understand I can revoke this license at any time by deleting the voice in my profile.`;

/** Hook: the signed-in user's licensed voices (live list for the Create tab). */
export function useLicensedVoices() {
  const [voices, setVoices] = useState<LicensedVoice[]>([]);
  const reload = useCallback(() => {
    api<{ voices: LicensedVoice[] }>("/api/studio/voices")
      .then((r) => setVoices(r.voices))
      .catch(() => {});
  }, []);
  useEffect(() => reload(), [reload]);
  return { voices, reload };
}

/* ---------------- Create-license panel (Create tab) ---------------- */

export function VoiceClonePanel({ user, onLicensed }: { user: StudioUser; onLicensed: () => void }) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [ownerType, setOwnerType] = useState<"self" | "third-party">("self");
  const [sample, setSample] = useState<File | null>(null);
  const [consent, setConsent] = useState<File | null>(null);
  const [written, setWritten] = useState<File | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 inline-flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-primary hover:underline underline-offset-4"
      >
        <Mic className="h-3.5 w-3.5" aria-hidden /> Clone your own voice - license it in 2 minutes
      </button>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sample || !consent) { setError("Both audio files are required"); return; }
    setBusy(true); setError(""); setMsg("");
    try {
      const fd = new FormData();
      fd.append("label", label);
      fd.append("ownerType", ownerType);
      fd.append("acceptLicense", accepted ? "yes" : "no");
      fd.append("sample", sample);
      fd.append("consent", consent);
      if (written) fd.append("written", written);
      const res = await api<{ message: string }>("/api/studio/voices", { method: "POST", body: fd });
      setMsg(res.message);
      setLabel(""); setSample(null); setConsent(null); setWritten(null); setAccepted(false);
      onLicensed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not license the voice");
    } finally {
      setBusy(false);
    }
  }

  const fileChip = (f: File | null) => (f ? `${f.name} (${Math.max(1, Math.round(f.size / 1024))} KB)` : "");

  return (
    <form onSubmit={submit} className="mt-2 border border-white/20 bg-white/5 p-4 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-black uppercase tracking-widest flex items-center gap-2">
          <Mic className="h-4 w-4 text-primary" aria-hidden /> Voice clone licensing
        </p>
        <button type="button" onClick={() => setOpen(false)} className="text-white/50 hover:text-white text-xs font-bold uppercase tracking-widest" aria-label="Close voice licensing">Close</button>
      </div>
      <p className="text-[11px] leading-relaxed text-white/60">
        Only a voice you own - or one with the owner&apos;s written permission - may be licensed here.
        Your consent recording is the license evidence, exactly how the big platforms verify voice ownership
        (and what the ELVIS Act &amp; Nigeria&apos;s NDPA expect). Read the statement aloud clearly.
      </p>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="vc-label" className="text-[10px] font-black uppercase tracking-widest text-white/70">Voice name</Label>
          <Input id="vc-label" required maxLength={60} value={label} onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. My voice" className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-[10px] font-black uppercase tracking-widest text-white/70">Whose voice?</Label>
          <div className="flex gap-2">
            {(["self", "third-party"] as const).map((t) => (
              <button key={t} type="button" onClick={() => setOwnerType(t)} aria-pressed={ownerType === t}
                className={`flex-1 px-2 py-2 text-[10px] font-black uppercase tracking-widest border-2 ${
                  ownerType === t ? "border-primary bg-primary/10 text-white" : "border-white/20 text-white/60 hover:text-white"
                }`}>
                {t === "self" ? "My own voice" : "Someone else's"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <label className="space-y-1.5 block">
          <span className="text-[10px] font-black uppercase tracking-widest text-white/70">1 - Voice sample (10s+ clean speech)</span>
          <span className="h-10 flex items-center gap-2 border border-white/25 px-3 text-xs text-white/70 hover:text-white cursor-pointer w-full justify-center">
            {fileChip(sample) || <><Upload className="h-3.5 w-3.5" aria-hidden /> Upload audio (WAV/MP3/M4A/OGG)</>}
            <input type="file" accept="audio/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setSample(f); }} />
          </span>
        </label>
        <label className="space-y-1.5 block">
          <span className="text-[10px] font-black uppercase tracking-widest text-white/70">2 - Consent recording (read the statement)</span>
          <span className="h-10 flex items-center gap-2 border border-white/25 px-3 text-xs text-white/70 hover:text-white cursor-pointer w-full justify-center">
            {fileChip(consent) || <><Upload className="h-3.5 w-3.5" aria-hidden /> Upload consent audio</>}
            <input type="file" accept="audio/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setConsent(f); }} />
          </span>
        </label>
      </div>

      <div className="border border-white/15 bg-black/30 p-3">
        <p className="text-[10px] font-black uppercase tracking-widest text-white/50">Read this exact statement aloud for the consent recording:</p>
        <p className="mt-2 text-sm leading-relaxed text-white/85">&ldquo;{CONSENT_PHRASE(user.name)}&rdquo;</p>
      </div>

      {ownerType === "third-party" && (
        <label className="space-y-1.5 block">
          <span className="text-[10px] font-black uppercase tracking-widest text-white/70">3 - Signed written permission (PDF/JPEG/PNG)</span>
          <span className="h-10 flex items-center gap-2 border border-white/25 px-3 text-xs text-white/70 hover:text-white cursor-pointer w-full justify-center">
            {fileChip(written) || <><Upload className="h-3.5 w-3.5" aria-hidden /> Upload permission document</>}
            <input type="file" accept="application/pdf,image/jpeg,image/png" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setWritten(f); }} />
          </span>
          <span className="block text-[10px] text-white/40">Third-party voices activate after the DeYoung owner reviews the document.</span>
        </label>
      )}

      <label className="flex items-start gap-2.5 text-[11px] leading-relaxed text-white/70">
        <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)}
          className="mt-0.5 accent-[#DC2626]" />
        <span>
          I accept the{" "}
          <a href="#voice-license" className="underline underline-offset-2 text-primary font-bold" target="_blank" rel="noreferrer">
            Voice Clone License &amp; Consent Policy
          </a>
          . I am the voice owner or hold written permission, I will not use this voice to impersonate or deceive
          anyone, and I understand DeYoung audits every clone and revokes licenses that break the rules.
        </span>
      </label>

      {error && <p className="text-sm text-primary font-semibold" role="alert">{error}</p>}
      {msg && <p className="text-sm font-semibold text-white bg-white/10 border border-white/20 px-3 py-2 flex items-center gap-2"><BadgeCheck className="h-4 w-4 text-primary" aria-hidden /> {msg}</p>}

      <Button type="submit" disabled={busy || !accepted || !label || !sample || !consent || (ownerType === "third-party" && !written)}
        className="w-full bg-primary hover:bg-[#B91C1C] text-white font-bold">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
        {busy ? "Filing the license…" : "License this voice"}
      </Button>
    </form>
  );
}

/* ---------------- License list (Profile tab) ---------------- */

export function VoiceLicenseList({ voices, onRevoked }: { voices: LicensedVoice[]; onRevoked: () => void }) {
  const [busyId, setBusyId] = useState("");

  async function revoke(id: string) {
    setBusyId(id);
    try {
      await api(`/api/studio/voices?id=${encodeURIComponent(id)}`, { method: "DELETE" });
      onRevoked();
    } finally {
      setBusyId("");
    }
  }

  if (voices.length === 0) {
    return (
      <p className="mt-2 text-sm text-white/60 leading-relaxed">
        No licensed voices yet. License your voice from the Create tab - a voice sample plus your consent
        recording is all it takes.
      </p>
    );
  }

  return (
    <ul className="mt-3 space-y-2">
      {voices.map((v) => (
        <li key={v.id} className="border border-white/15 bg-white/5 px-3.5 py-3 flex items-center gap-3 flex-wrap">
          <Mic className="h-4 w-4 text-primary shrink-0" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold">{v.label}</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
              {v.ownerType === "self" ? "own voice" : "third-party"} · license {v.licenseVersion} · {new Date(v.createdAt).toLocaleDateString()}
            </p>
          </div>
          <VoiceStatusChip v={v} />
          {v.status === "licensed" && (
            <Button variant="outline" size="sm" disabled={busyId === v.id} onClick={() => revoke(v.id)}
              className="border-white/25 text-white/70 hover:bg-primary hover:text-white hover:border-primary font-bold">
              {busyId === v.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Trash2 className="h-3.5 w-3.5" aria-hidden />}
              Revoke
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}

export function VoiceStatusChip({ v }: { v: LicensedVoice }) {
  const map: Record<string, string> = {
    licensed: "bg-green-500/15 text-green-400",
    pending: "bg-amber-500/15 text-amber-400",
    rejected: "bg-red-500/15 text-red-400",
    revoked: "bg-white/10 text-white/50 line-through",
  };
  const label = v.status === "licensed"
    ? (v.ownerType === "third-party" && v.reviewStatus !== "approved" ? "licensed · audit pending" : "licensed")
    : v.status;
  return (
    <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-1 whitespace-nowrap ${map[v.status] ?? map.pending}`}>
      {label}
    </span>
  );
}

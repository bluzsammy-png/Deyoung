"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Flag, Loader2, Mic, ShieldAlert, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { api } from "@/lib/types";

/**
 * Voice Licenses (admin) - the audit half of the voice-cloning license.
 * Every license on file with its evidence: the voice sample, the consent
 * recording, and (for third-party voices) the written permission document.
 * The owner listens/reviews and approves, flags, rejects, revokes or
 * reinstates. Consent evidence is kept for the life of the license.
 */

type AdminVoice = {
  id: string;
  userId: string;
  userEmail: string;
  label: string;
  ownerType: string; // self | third-party
  sampleUrl: string;
  consentUrl: string;
  writtenConsentUrl: string;
  licenseVersion: string;
  status: string; // licensed | pending | rejected | revoked
  reviewStatus: string; // pending | approved | flagged
  reviewNotes: string;
  createdAt: string;
  revokedAt: string | null;
};

export function AdminVoices() {
  const [voices, setVoices] = useState<AdminVoice[] | null>(null);
  const [busyId, setBusyId] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = () => {
    api<{ voices: AdminVoice[] }>("/api/admin/voices")
      .then((r) => setVoices(r.voices))
      .catch(() => setVoices([]));
  };
  useEffect(load, []);

  async function act(id: string, action: string) {
    setBusyId(id + action);
    try {
      await api("/api/admin/voices", {
        method: "PATCH",
        body: JSON.stringify({ id, action, notes: notes[id] || "" }),
      });
      toast.success(`Voice ${action}d`);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId("");
    }
  }

  if (!voices) return <p className="text-muted-foreground p-4">Loading voice licenses…</p>;
  if (voices.length === 0) {
    return (
      <div className="bg-white border-2 border-neutral-200 p-8 text-center">
        <Mic className="h-6 w-6 mx-auto text-primary" aria-hidden />
        <p className="mt-3 font-black uppercase tracking-tight">No voice licenses yet</p>
        <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
          When customers license their voice (sample + consent recording) the license and all its
          evidence appear here for your audit.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground leading-relaxed">
        {voices.length} license{voices.length === 1 ? "" : "s"} on file. Self-voice licenses activate
        instantly on the customer&apos;s consent recording; third-party licenses wait for your approval.
        Listen to the evidence before approving, and revoke anything that looks like impersonation -
        the license agreement puts that duty on the platform (ELVIS Act / NDPA discipline).
      </p>
      {voices.map((v) => (
        <div key={v.id} className="bg-white border-2 border-neutral-200 p-5">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="font-black tracking-tight">
                {v.label}{" "}
                <span className="text-xs font-bold text-muted-foreground">- {v.userEmail}</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {v.ownerType === "self" ? "Own voice" : "Third-party voice"} · license {v.licenseVersion} · filed{" "}
                {new Date(v.createdAt).toLocaleString()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusChip status={v.status} />
              <ReviewChip status={v.reviewStatus} />
            </div>
          </div>

          <div className="mt-4 grid md:grid-cols-2 gap-4">
            <EvidenceAudio label="Voice sample" src={v.sampleUrl} />
            <EvidenceAudio label="Consent recording (the license evidence)" src={v.consentUrl} />
            {v.writtenConsentUrl && (
              <p className="text-sm md:col-span-2">
                Written permission:{" "}
                <a href={v.writtenConsentUrl} target="_blank" rel="noreferrer"
                  className="font-bold text-primary hover:underline underline-offset-4">
                  open document
                </a>
              </p>
            )}
          </div>

          {v.reviewNotes && (
            <p className="mt-3 text-xs text-muted-foreground"><strong>Notes:</strong> {v.reviewNotes}</p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Input
              value={notes[v.id] ?? ""}
              onChange={(e) => setNotes({ ...notes, [v.id]: e.target.value })}
              placeholder="Review note (optional)"
              className="max-w-xs h-9 text-sm"
            />
            <Button size="sm" disabled={busyId === v.id + "approve"} onClick={() => act(v.id, "approve")}
              className="bg-[var(--brand-black)] hover:bg-black text-white font-bold">
              {busyId === v.id + "approve" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />}
              Approve
            </Button>
            <Button size="sm" variant="outline" disabled={busyId === v.id + "flag"} onClick={() => act(v.id, "flag")}
              className="border-amber-400 text-amber-600 hover:bg-amber-50 font-bold">
              <Flag className="h-3.5 w-3.5" aria-hidden /> Flag
            </Button>
            <Button size="sm" variant="outline" disabled={busyId === v.id + "reject"} onClick={() => act(v.id, "reject")}
              className="border-neutral-300 text-neutral-600 font-bold">
              <ShieldAlert className="h-3.5 w-3.5" aria-hidden /> Reject
            </Button>
            {v.status === "licensed" ? (
              <Button size="sm" variant="outline" disabled={busyId === v.id + "revoke"} onClick={() => act(v.id, "revoke")}
                className="border-primary text-primary hover:bg-primary hover:text-white font-bold">
                Revoke
              </Button>
            ) : (
              <Button size="sm" variant="outline" disabled={busyId === v.id + "reinstate"} onClick={() => act(v.id, "reinstate")}
                className="border-neutral-300 text-neutral-600 font-bold">
                <Undo2 className="h-3.5 w-3.5" aria-hidden /> Reinstate
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    licensed: "bg-green-100 text-green-700",
    pending: "bg-amber-100 text-amber-700",
    rejected: "bg-neutral-200 text-neutral-500",
    revoked: "bg-red-100 text-red-600 line-through",
  };
  return <span className={`text-[10px] font-black uppercase px-2 py-1 ${map[status] ?? map.pending}`}>{status}</span>;
}

function ReviewChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-neutral-100 text-neutral-500",
    approved: "bg-green-100 text-green-700",
    flagged: "bg-amber-100 text-amber-700",
  };
  return <span className={`text-[10px] font-black uppercase px-2 py-1 ${map[status] ?? map.pending}`}>audit: {status}</span>;
}

function EvidenceAudio({ label, src }: { label: string; src: string }) {
  return (
    <div className="border border-neutral-200 p-3">
      <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{label}</p>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption -- consent evidence clips */}
      <audio controls preload="none" src={src} className="mt-2 w-full h-9" />
    </div>
  );
}

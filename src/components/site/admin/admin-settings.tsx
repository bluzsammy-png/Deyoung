"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2, Lock, Plus, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api, type Faq, type PublicSettings, type Testimonial } from "@/lib/types";
import { AdminPanel } from "./admin-content";

/* ---------------- Reviews & FAQ ---------------- */

export function AdminContentTab() {
  const [testimonials, setTestimonials] = useState<Testimonial[] | null>(null);
  const [faqs, setFaqs] = useState<Faq[] | null>(null);
  const [tDraft, setTDraft] = useState({ name: "", role: "", quote: "" });
  const [fDraft, setFDraft] = useState({ question: "", answer: "" });

  const load = useCallback(() => {
    api<{ testimonials: Testimonial[] }>("/api/testimonials").then((r) => setTestimonials(r.testimonials)).catch(() => setTestimonials([]));
    api<{ faqs: Faq[] }>("/api/faqs").then((r) => setFaqs(r.faqs)).catch(() => setFaqs([]));
  }, []);

  useEffect(load, [load]);

  if (!testimonials || !faqs) return <p className="text-muted-foreground">Loading content…</p>;

  return (
    <div className="space-y-6">
      <AdminPanel title={`Client reviews (${testimonials.length})`}>
        <ul className="space-y-3">
          {testimonials.map((t) => (
            <li key={t.id} className="border-2 border-neutral-100 p-4 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold">{t.name}</span>
                {t.role ? <span className="text-muted-foreground">· {t.role}</span> : null}
                <div className="ml-auto flex items-center gap-2">
                  <Switch
                    checked={t.active}
                    onCheckedChange={(v) => api(`/api/testimonials/${t.id}`, { method: "PATCH", body: JSON.stringify({ active: v }) }).then(load)}
                    aria-label={`Show review from ${t.name}`}
                  />
                  <Button size="icon" variant="ghost" aria-label={`Delete review from ${t.name}`} onClick={async () => { if (!confirm("Delete review?")) return; await api(`/api/testimonials/${t.id}`, { method: "DELETE" }); load(); }}>
                    <Trash2 className="h-4 w-4 text-neutral-400 hover:text-destructive" />
                  </Button>
                </div>
              </div>
              <p className="mt-1 text-neutral-600">&ldquo;{t.quote}&rdquo;</p>
            </li>
          ))}
        </ul>
        <div className="mt-5 border-t-2 pt-5 grid sm:grid-cols-[1fr_1fr] gap-3">
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="tr-name">Client name</Label>
              <Input id="tr-name" value={tDraft.name} onChange={(e) => setTDraft({ ...tDraft, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tr-role">Role (optional)</Label>
              <Input id="tr-role" value={tDraft.role} onChange={(e) => setTDraft({ ...tDraft, role: e.target.value })} placeholder="e.g. Boutique owner" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tr-quote">Quote</Label>
            <Textarea id="tr-quote" rows={3} value={tDraft.quote} onChange={(e) => setTDraft({ ...tDraft, quote: e.target.value })} />
            <Button
              size="sm" className="bg-primary hover:bg-[#B91C1C] text-white font-bold"
              onClick={async () => {
                if (!tDraft.name || !tDraft.quote) return toast.error("Name and quote are required");
                await api("/api/testimonials", { method: "POST", body: JSON.stringify(tDraft) });
                toast.success("Review added");
                setTDraft({ name: "", role: "", quote: "" });
                load();
              }}
            >
              <Plus className="h-4 w-4" aria-hidden /> Add review
            </Button>
          </div>
        </div>
      </AdminPanel>

      <AdminPanel title={`FAQ (${faqs.length})`}>
        <ul className="space-y-3">
          {faqs.map((f) => (
            <li key={f.id} className="border-2 border-neutral-100 p-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-bold">{f.question}</span>
                <div className="ml-auto flex items-center gap-2">
                  <Switch
                    checked={f.active}
                    onCheckedChange={(v) => api(`/api/faqs/${f.id}`, { method: "PATCH", body: JSON.stringify({ active: v }) }).then(load)}
                    aria-label={`Show FAQ: ${f.question}`}
                  />
                  <Button size="icon" variant="ghost" aria-label="Delete FAQ" onClick={async () => { if (!confirm("Delete FAQ?")) return; await api(`/api/faqs/${f.id}`, { method: "DELETE" }); load(); }}>
                    <Trash2 className="h-4 w-4 text-neutral-400 hover:text-destructive" />
                  </Button>
                </div>
              </div>
              <p className="mt-1 text-neutral-600">{f.answer}</p>
            </li>
          ))}
        </ul>
        <div className="mt-5 border-t-2 pt-5 space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="fq-q">Question</Label>
            <Input id="fq-q" value={fDraft.question} onChange={(e) => setFDraft({ ...fDraft, question: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="fq-a">Answer</Label>
            <Textarea id="fq-a" rows={3} value={fDraft.answer} onChange={(e) => setFDraft({ ...fDraft, answer: e.target.value })} />
          </div>
          <Button
            size="sm" className="bg-primary hover:bg-[#B91C1C] text-white font-bold"
            onClick={async () => {
              if (!fDraft.question || !fDraft.answer) return toast.error("Question and answer are required");
              await api("/api/faqs", { method: "POST", body: JSON.stringify(fDraft) });
              toast.success("FAQ added");
              setFDraft({ question: "", answer: "" });
              load();
            }}
          >
            <Plus className="h-4 w-4" aria-hidden /> Add FAQ
          </Button>
        </div>
      </AdminPanel>
    </div>
  );
}

/* ---------------- Payments ---------------- */

const PROVIDERS = [
  {
    key: "manual",
    name: "Bank transfer / Mobile money",
    free: "No signup needed - works today",
    how: "Enter your bank / mobile money details below. Customers see them at checkout and pay you directly.",
    signupUrl: "",
  },
  {
    key: "paystack",
    name: "Paystack",
    free: "Free to sign up · local + international cards · recommended",
    how: "Sign up at paystack.com as a STARTER BUSINESS - BVN + NIN slip + phone number is enough, no CAC needed. Test mode works instantly; go-live review is usually 24-72 hours. Copy your PUBLIC key (pk_…) and SECRET key (sk_…) into the fields below.",
    signupUrl: "https://paystack.com/signup",
  },
  {
    key: "flutterwave",
    name: "Flutterwave",
    free: "Free to sign up · local + international cards",
    how: "Sign up at flutterwave.com, get your PUBLIC key (FLWPUBK_…) and SECRET key (FLWSECK_…) from Settings → API.",
    signupUrl: "https://dashboard.flutterwave.com/",
  },
  {
    key: "paypal",
    name: "PayPal",
    free: "Free to sign up · works worldwide",
    how: "Create a PayPal business account, then in Developer → Apps & Credentials create a Live app and paste the Client ID and Secret.",
    signupUrl: "https://www.paypal.com/",
  },
  {
    key: "stripe",
    name: "Stripe Payment Link",
    free: "Free to sign up · international cards",
    how: "Sign up at stripe.com, create a Payment Link for each price, paste one link below (simplest card option).",
    signupUrl: "https://dashboard.stripe.com/register",
  },
] as const;

export function AdminPayments() {
  const [s, setS] = useState<PublicSettings | null>(null);
  const [secret, setSecret] = useState("");
  const [hasSecret, setHasSecret] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api<{ settings: PublicSettings }>("/api/settings").then((r) => setS(r.settings)).catch(() => null);
    // fetch full settings (with key presence) via admin-only PUT is overkill; read public + secret presence:
    fetch("/api/admin/payments-meta")
      .then((r) => r.json())
      .then((d: { hasSecret?: boolean; secretPreview?: string }) => {
        setHasSecret(!!d.hasSecret);
        if (d.secretPreview) setSecret(d.secretPreview);
      })
      .catch(() => null);
  }, []);

  if (!s) return <p className="text-muted-foreground">Loading payment settings…</p>;

  async function save() {
    if (!s) return;
    setSaving(true);
    try {
      await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          ...s,
          paymentSecretKey: secret || undefined,
        }),
      });
      toast.success("Payment settings saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const p = PROVIDERS.find((x) => x.key === s.paymentProvider) ?? PROVIDERS[0];

  return (
    <AdminPanel
      title="Payment method"
      action={
        <Button size="sm" onClick={save} disabled={saving} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Check className="h-4 w-4" aria-hidden />} Save
        </Button>
      }
    >
      <div className="space-y-6">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {PROVIDERS.map((x) => (
            <button
              key={x.key}
              onClick={() => setS({ ...s, paymentProvider: x.key })}
              aria-pressed={s.paymentProvider === x.key}
              className={`text-left border-2 p-4 transition-colors ${
                s.paymentProvider === x.key ? "border-primary bg-[#FFF8F8]" : "border-neutral-200 hover:border-neutral-400"
              }`}
            >
              <p className="font-black text-sm">{x.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">{x.free}</p>
            </button>
          ))}
        </div>

        <div className="border-2 border-neutral-100 p-4 space-y-4">
          <div>
            <p className="font-black uppercase text-sm">{p.name}</p>
            <p className="text-sm text-muted-foreground mt-1">{p.how}</p>
            {p.signupUrl ? (
              <a
                href={p.signupUrl} target="_blank" rel="noopener noreferrer"
                className="inline-block mt-2 text-sm font-bold text-primary underline underline-offset-4"
              >
                Create free {p.name} account ↗
              </a>
            ) : null}
          </div>

          {s.paymentProvider === "paystack" && (
            <div className="border-2 border-primary/40 bg-[#FFF8F8] p-4 space-y-2">
              <p className="font-black uppercase text-xs tracking-widest text-primary">Zero-stress go-live checklist</p>
              <ol className="text-sm space-y-1.5 list-decimal list-inside text-neutral-700">
                <li>Sign up at paystack.com → choose <strong>Starter Business</strong> (your BVN + NIN slip + phone number are enough - no CAC required).</li>
                <li>Verify your email, add your bank account for payouts (T+1 settlement).</li>
                <li>Test mode works instantly - use the pk_test/sk_test keys first and pay yourself ₦100 to see the flow.</li>
                <li>Finish identity verification (BVN + NIN + a utility bill photo is the usual ask) → keys flip to live.</li>
                <li>Paste both live keys here, set currency (NGN for naira cards; USD prices are converted by Paystack at checkout for international cards).</li>
                <li>Add the webhook in Paystack Dashboard → Settings → API Keys &amp; Webhooks: <code className="font-mono text-xs">https://your-domain/api/payments/webhook/paystack</code> - subscriptions and bookings then activate automatically, even if the customer closes the tab.</li>
              </ol>
              <p className="text-xs text-muted-foreground">Fees: 1.5% + ₦100 per local transaction (capped), 3.9% + ₦100 international. No monthly fee, no setup fee.</p>
            </div>
          )}

          {["paystack", "flutterwave", "paypal"].includes(s.paymentProvider) && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="pm-pub">{s.paymentProvider === "paypal" ? "Client ID" : "Public key"}</Label>
                <Input id="pm-pub" value={s.paymentPublicKey} onChange={(e) => setS({ ...s, paymentPublicKey: e.target.value })} placeholder="pk_… / FLWPUBK_… / Client ID" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pm-sec">{s.paymentProvider === "paypal" ? "Secret" : "Secret key (for automatic payment verification)"}</Label>
                <Input id="pm-sec" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} placeholder={hasSecret ? "Saved - type a new one to replace" : "sk_… / Secret"} />
              </div>
            </>
          )}

          {s.paymentProvider === "stripe" && (
            <div className="space-y-1.5">
              <Label htmlFor="pm-link">Payment link URL</Label>
              <Input id="pm-link" value={s.paymentLinkUrl} onChange={(e) => setS({ ...s, paymentLinkUrl: e.target.value })} placeholder="https://buy.stripe.com/…" />
            </div>
          )}

          {s.paymentProvider === "manual" && (
            <div className="space-y-1.5">
              <Label htmlFor="pm-bank">Bank / mobile money details shown to customers</Label>
              <Textarea id="pm-bank" rows={4} value={s.bankDetails} onChange={(e) => setS({ ...s, bankDetails: e.target.value })} placeholder={"Bank: …\nAccount name: …\nAccount number: …\nMobile money: …"} />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="pm-cur">Currency code</Label>
            <Input id="pm-cur" maxLength={5} value={s.currency} onChange={(e) => setS({ ...s, currency: e.target.value.toUpperCase() })} placeholder="USD / NGN / GHS / KES / EUR" />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="pm-instr">Payment instructions (manual method)</Label>
            <Textarea id="pm-instr" rows={3} value={s.paymentInstructions} onChange={(e) => setS({ ...s, paymentInstructions: e.target.value })} />
          </div>
        </div>
      </div>
    </AdminPanel>
  );
}

/* ---------------- Site & Profile ---------------- */

export function AdminSettings() {
  const [s, setS] = useState<(PublicSettings & { heroTitle?: string; heroSubtitle?: string; aboutTitle?: string }) | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api<{ settings: PublicSettings }>("/api/settings").then((r) => setS(r.settings)).catch(() => null);
    fetch("/api/admin/full-settings")
      .then((r) => r.json())
      .then((d: { settings?: Record<string, string> }) => {
        if (d.settings) setS((prev) => (prev ? { ...prev, ...d.settings } : prev));
      })
      .catch(() => null);
  }, []);

  if (!s) return <p className="text-muted-foreground">Loading settings…</p>;

  async function save() {
    setSaving(true);
    try {
      const { paymentSecretKey: _drop, ...payload } = s as PublicSettings & Record<string, unknown>;
      await api("/api/settings", { method: "PUT", body: JSON.stringify(payload) });
      toast.success("Site settings saved - refresh the site to see changes");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function uploadPhoto(file: File) {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api<{ url: string }>("/api/upload", { method: "POST", body: fd });
      setS((prev) => (prev ? { ...prev, ownerPhotoUrl: res.url } : prev));
      toast.success("Photo uploaded - press Save to apply");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  let socialMap: Record<string, string> = {};
  try {
    socialMap = JSON.parse(s.socialJson || "{}");
  } catch {
    socialMap = {};
  }
  const setSocial = (k: string, v: string) => {
    socialMap = { ...socialMap, [k]: v };
    setS({ ...s, socialJson: JSON.stringify(socialMap) });
  };

  const F = ({ id, label, value, onChange, textarea, rows, placeholder }: {
    id: string; label: string; value: string; onChange: (v: string) => void;
    textarea?: boolean; rows?: number; placeholder?: string;
  }) => (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {textarea ? (
        <Textarea id={id} rows={rows ?? 3} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      ) : (
        <Input id={id} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      )}
    </div>
  );

  return (
    <AdminPanel
      title="Site & profile"
      action={
        <Button size="sm" onClick={save} disabled={saving} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Check className="h-4 w-4" aria-hidden />} Save
        </Button>
      }
    >
      <div className="space-y-8">
        <section className="space-y-4">
          <h3 className="font-black uppercase text-sm tracking-wide">Brand</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            <F id="st-name" label="Site name" value={s.siteName} onChange={(v) => setS({ ...s, siteName: v })} />
            <F id="st-tag" label="Tagline" value={s.tagline} onChange={(v) => setS({ ...s, tagline: v })} />
          </div>
          <F id="st-hero" label="Hero big title" value={s.heroTitle ?? "DEYOUNG"} onChange={(v) => setS({ ...s, heroTitle: v })} />
          <F id="st-hsub" label="Hero subtitle" textarea rows={2} value={s.heroSubtitle ?? ""} onChange={(v) => setS({ ...s, heroSubtitle: v })} />
        </section>

        <section className="space-y-4">
          <h3 className="font-black uppercase text-sm tracking-wide">Owner profile & photo</h3>
          <div className="flex items-center gap-4">
            {s.ownerPhotoUrl ? (
              <img src={s.ownerPhotoUrl} alt="Owner photo preview" className="h-20 w-20 object-cover border-2 border-primary" />
            ) : null}
            <div>
              <input
                ref={fileRef} type="file" accept="image/*" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadPhoto(f); }}
              />
              <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading}>
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
                Upload your picture
              </Button>
              <p className="text-xs text-muted-foreground mt-1">JPG/PNG/WebP, max 8MB. Shows in hero + about.</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <F id="st-owner" label="Owner name" value={s.ownerName} onChange={(v) => setS({ ...s, ownerName: v })} />
            <F id="st-otitle" label="Owner title" value={s.ownerTitle} onChange={(v) => setS({ ...s, ownerTitle: v })} />
          </div>
          <F id="st-atitle" label="About section title" value={s.aboutTitle ?? ""} onChange={(v) => setS({ ...s, aboutTitle: v })} />
          <F id="st-about" label="About text" textarea rows={5} value={s.aboutBody} onChange={(v) => setS({ ...s, aboutBody: v })} />
        </section>

        <section className="space-y-4">
          <h3 className="font-black uppercase text-sm tracking-wide">Contact</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            <F id="st-email" label="Email" value={s.contactEmail} onChange={(v) => setS({ ...s, contactEmail: v })} />
            <F id="st-phone" label="Phone" value={s.phone} onChange={(v) => setS({ ...s, phone: v })} />
            <F id="st-wa" label="WhatsApp number (digits only)" value={s.whatsapp} onChange={(v) => setS({ ...s, whatsapp: v })} />
            <F id="st-loc" label="Location" value={s.location} onChange={(v) => setS({ ...s, location: v })} />
          </div>
          <F id="st-resp" label="Response time promise" value={s.responseTime} onChange={(v) => setS({ ...s, responseTime: v })} />
        </section>

        <section className="space-y-4">
          <h3 className="font-black uppercase text-sm tracking-wide">Social links</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            {["instagram", "tiktok", "x", "facebook", "youtube"].map((k) => (
              <F
                key={k}
                id={`so-${k}`}
                label={k === "x" ? "X (Twitter)" : k.charAt(0).toUpperCase() + k.slice(1)}
                value={socialMap[k] ?? ""}
                onChange={(v) => setSocial(k, v)}
                placeholder="https://…"
              />
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <h3 className="font-black uppercase text-sm tracking-wide">SEO</h3>
          <F id="st-meta" label="Meta description (what Google shows)" textarea rows={2} value={s.metaDescription} onChange={(v) => setS({ ...s, metaDescription: v })} />
        </section>
      </div>
    </AdminPanel>
  );
}

/* ---------------- Security ---------------- */

export function AdminSecurity({ onDone }: { onDone?: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ currentPassword: current, newPassword: next }),
      });
      toast.success("Password changed - you own this panel.");
      setCurrent("");
      setNext("");
      onDone?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Change failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminPanel title="Change your password">
      <form onSubmit={submit} className="max-w-md space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="pw-cur">Current password</Label>
          <Input id="pw-cur" type="password" required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pw-new">New password (min 8 characters)</Label>
          <Input id="pw-new" type="password" required minLength={8} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <Button type="submit" disabled={busy} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Lock className="h-4 w-4" aria-hidden />}
          Update password
        </Button>
        <p className="text-xs text-muted-foreground">
          Only you (the owner) can log in. Sessions expire after 7 days and passwords are stored salted &amp; hashed.
        </p>
      </form>
    </AdminPanel>
  );
}

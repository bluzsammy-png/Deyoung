"use client";

import { useState } from "react";
import Image from "next/image";
import { Star, Clock, ArrowRight, Mail, Phone, MapPin, Instagram, Twitter, Facebook, Youtube, Send, X, PenLine, Clapperboard, Download, ChevronRight } from "lucide-react";
import { LogoMark } from "./logo";
import { TiltCard, Reveal } from "./motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { toast } from "sonner";
import { api, money, type Faq, type HomeData, type Photo, type PublicSettings, type Service, type Testimonial } from "@/lib/types";
import { go } from "./hash";

/* ---------------- Services ---------------- */

export function Services({ services, currency }: { services: Service[]; currency: string }) {
  return (
    <section id="services" className="scroll-mt-20 py-16 md:py-24 bg-white">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHead kicker="What you can book" title="Services & Pricing" dark={false} />
        {services.length === 0 ? (
          <p className="text-muted-foreground">Services are being updated - check back soon or send a message.</p>
        ) : (
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 dy-scene">
            {services.map((s, i) => (
              <Reveal key={s.id} delay={(i % 4) * 80}>
              <TiltCard className="h-full">
              <article
                className="group border-2 border-neutral-200 hover:border-primary transition-colors flex flex-col bg-white h-full"
              >
                <div className="h-1.5 bg-primary opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="font-black text-lg uppercase tracking-tight">{s.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-relaxed flex-1">{s.description}</p>
                  {s.duration ? (
                    <p className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-neutral-500">
                      <Clock className="h-3.5 w-3.5 text-primary" aria-hidden /> {s.duration}
                    </p>
                  ) : null}
                  <p className="mt-4 flex flex-wrap items-center gap-2">
                    <span className="text-3xl font-black tracking-tight">{money(s.price, currency)}</span>
                    {s.compareAtPrice && s.compareAtPrice > s.price ? (
                      <>
                        <span className="text-sm font-bold text-neutral-400 line-through">
                          {money(s.compareAtPrice, currency)}
                        </span>
                        <span className="bg-primary text-white text-[10px] font-black uppercase tracking-widest px-1.5 py-0.5">
                          Save {Math.round(((s.compareAtPrice - s.price) / s.compareAtPrice) * 100)}%
                        </span>
                      </>
                    ) : null}
                  </p>
                  <p className="mt-1 text-[11px] font-semibold uppercase tracking-widest text-primary">
                    New rate - rises again soon
                  </p>
                  <Button
                    onClick={() => go(`#book?service=${s.id}`)}
                    className="mt-4 w-full bg-[var(--brand-black)] hover:bg-primary text-white font-bold"
                  >
                    Book This <ArrowRight className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              </article>
              </TiltCard>
              </Reveal>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

/* ---------------- Gallery (works by category) ---------------- */

const ALL_CATS = ["Portrait", "Brand", "Editorial", "Event", "Studio", "Commercial"] as const;

function catOf(title: string): string {
  const c = title.split(":")[0].trim();
  return (ALL_CATS as readonly string[]).includes(c) ? c : "Portrait";
}

export function Gallery({ photos }: { photos: Photo[] }) {
  const [active, setActive] = useState<Photo | null>(null);
  const [cat, setCat] = useState<string>("All");

  const cats = ["All", ...ALL_CATS.filter((c) => photos.some((p) => catOf(p.title) === c))];
  const shown = cat === "All" ? photos : photos.filter((p) => catOf(p.title) === cat);

  return (
    <section id="gallery" className="scroll-mt-20 py-16 md:py-24 bg-[var(--brand-black)] text-white">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHead kicker="Recent work" title="The Work Speaks" dark />
        <p className="mt-4 max-w-2xl text-white/60 leading-relaxed">
          Real deliverables, filed the way clients book them. Pick a category - portrait sessions,
          brand packs, editorial spreads, event coverage, studio work and commercials.
        </p>

        {/* category tabs */}
        <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Work categories">
          {cats.map((c) => (
            <button
              key={c}
              role="tab"
              aria-selected={cat === c}
              onClick={() => setCat(c)}
              className={`px-4 py-2 text-xs font-black uppercase tracking-[0.15em] border-2 transition-colors ${
                cat === c
                  ? "bg-primary border-primary text-white"
                  : "border-white/20 text-white/70 hover:border-primary hover:text-white"
              }`}
            >
              {c}
              <span className="ml-2 opacity-60">
                {c === "All" ? photos.length : photos.filter((p) => catOf(p.title) === c).length}
              </span>
            </button>
          ))}
        </div>

        {shown.length === 0 ? (
          <p className="mt-10 text-white/60">New work is being uploaded - check back soon.</p>
        ) : (
          <div className="mt-10 grid grid-cols-2 md:grid-cols-3 gap-3">
            {shown.map((p, i) => (
              <Reveal key={p.id} delay={(i % 3) * 80}>
              <button
                onClick={() => setActive(p)}
                className="group relative aspect-[4/3] w-full overflow-hidden bg-neutral-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary hover:shadow-[0_10px_40px_-10px_rgba(220,38,38,0.5)] transition-shadow"
                aria-label={`View work: ${p.title}`}
              >
                <Image
                  src={p.url}
                  alt={p.alt || p.title}
                  fill
                  sizes="(max-width: 768px) 50vw, 33vw"
                  className="object-cover transition-transform duration-300 group-hover:scale-105"
                />
                <span className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" aria-hidden />
                <span className="absolute top-2 left-2 bg-black/85 backdrop-blur-sm text-white text-[10px] md:text-xs font-black tracking-[0.2em] uppercase px-2 py-1 border-l-2 border-primary">
                  {catOf(p.title)}
                </span>
                <span className="absolute top-2 right-2 bg-white text-black text-[10px] font-black tracking-[0.2em] uppercase px-2 py-1 opacity-90">
                  DeYoung • 0{(i % 9) + 1}
                </span>
                <span className="absolute bottom-2 right-2 bg-primary text-white text-[10px] font-black tracking-[0.2em] uppercase px-2 py-1 translate-y-2 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition">
                  DeYoung Original
                </span>
              </button>
              </Reveal>
            ))}
          </div>
        )}
      </div>

      {active && (
        <div
          className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label={`Work: ${active.title}`}
          onClick={() => setActive(null)}
        >
          <button
            className="absolute top-4 right-4 p-2 text-white bg-white/10 hover:bg-primary"
            aria-label="Close preview"
            onClick={() => setActive(null)}
          >
            <X className="h-6 w-6" />
          </button>
          <figure className="relative w-full max-w-3xl" onClick={(e) => e.stopPropagation()}>
            <div className="relative aspect-[4/3] bg-neutral-900">
              <Image src={active.url} alt={active.alt || active.title} fill sizes="100vw" className="object-contain" />
            </div>
            <figcaption className="mt-3 text-center text-sm text-white/70">
              <span className="text-primary font-black uppercase tracking-widest mr-2">{catOf(active.title)}</span>
              {active.title.split(":").slice(1).join(":").trim() || active.title}
            </figcaption>
          </figure>
        </div>
      )}
    </section>
  );
}

/* ---------------- About ---------------- */

export function About({ settings }: { settings: PublicSettings | null }) {
  const s = settings;
  return (
    <section id="about" className="scroll-mt-20 py-16 md:py-24 bg-white">
      <div className="mx-auto max-w-6xl px-4 grid md:grid-cols-[1fr_1.4fr] gap-10 items-center">
        <div className="relative max-w-xs mx-auto md:mx-0 w-full">
          <div className="absolute -bottom-3 -right-3 left-3 top-3 bg-primary" aria-hidden />
          <div className="relative aspect-square overflow-hidden bg-neutral-100">
            <Image
              src={s?.ownerPhotoUrl || "/img/avatar-default.png"}
              alt={`${s?.ownerName || "DeYoung"} - ${s?.ownerTitle || "creative professional"}`}
              fill
              sizes="(max-width: 768px) 80vw, 33vw"
              className="object-cover"
            />
          </div>
        </div>
        <div>
          <SectionHead kicker="The person behind it" title={s?.aboutTitle || "About DeYoung"} dark={false} />
          <p className="mt-6 text-base md:text-lg leading-relaxed text-neutral-700 whitespace-pre-line">
            {s?.aboutBody || "Story coming soon."}
          </p>
          {s?.location ? (
            <p className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-neutral-600">
              <MapPin className="h-4 w-4 text-primary" aria-hidden /> {s.location}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

/* ---------------- Testimonials ---------------- */

export function Testimonials({ testimonials }: { testimonials: Testimonial[] }) {
  if (testimonials.length === 0) return null;
  return (
    <section className="py-16 md:py-24 bg-[#F7F7F7] border-y-4 border-primary">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHead kicker="Real clients" title="Word on the Street" dark={false} />
        <div className="mt-10 grid md:grid-cols-3 gap-4 dy-scene">
          {testimonials.map((t, i) => (
            <Reveal key={t.id} delay={i * 90}>
            <TiltCard className="h-full">
            <figure className="bg-white border-2 border-neutral-200 p-6 flex flex-col h-full">
              <div className="flex gap-0.5" aria-label={`${t.rating} out of 5 stars`}>
                {Array.from({ length: t.rating }).map((_, i) => (
                  <Star key={i} className="h-4 w-4 fill-primary text-primary" aria-hidden />
                ))}
              </div>
              <blockquote className="mt-4 text-sm leading-relaxed text-neutral-700 flex-1">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <figcaption className="mt-4 pt-4 border-t">
                <p className="font-black text-sm uppercase">{t.name}</p>
                {t.role ? <p className="text-xs text-muted-foreground">{t.role}</p> : null}
              </figcaption>
            </figure>
            </TiltCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- FAQ ---------------- */

export function FaqSection({ faqs }: { faqs: Faq[] }) {
  return (
    <section id="faq" className="scroll-mt-20 py-16 md:py-24 bg-white">
      <div className="mx-auto max-w-3xl px-4">
        <SectionHead kicker="Answers" title="Questions, Handled" dark={false} />
        <Accordion type="single" collapsible className="mt-8">
          {faqs.map((f, i) => (
            <AccordionItem key={f.id} value={f.id} className="border-neutral-200">
              <AccordionTrigger className="text-left font-bold hover:text-primary hover:no-underline">
                {f.question}
              </AccordionTrigger>
              <AccordionContent className="text-neutral-600 leading-relaxed">{f.answer}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
        <p className="mt-6 text-sm text-neutral-500">
          Still unsure?{" "}
          <a href="#contact" className="font-bold text-primary underline underline-offset-4">
            Send a message
          </a>{" "}
          - no pressure.
        </p>
      </div>
    </section>
  );
}

/* ---------------- Contact ---------------- */

export function Contact({ settings }: { settings: PublicSettings | null }) {
  const s = settings;
  const [form, setForm] = useState({ name: "", email: "", body: "" });
  const [sending, setSending] = useState(false);

  const socials: { key: string; icon: typeof Instagram; label: string }[] = [
    { key: "instagram", icon: Instagram, label: "Instagram" },
    { key: "x", icon: Twitter, label: "X (Twitter)" },
    { key: "facebook", icon: Facebook, label: "Facebook" },
    { key: "youtube", icon: Youtube, label: "YouTube" },
  ];
  let socialMap: Record<string, string> = {};
  try {
    socialMap = JSON.parse(s?.socialJson || "{}");
  } catch {
    socialMap = {};
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    try {
      await api("/api/contact", { method: "POST", body: JSON.stringify(form) });
      toast.success("Message sent - you'll hear back soon.");
      setForm({ name: "", email: "", body: "" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not send message");
    } finally {
      setSending(false);
    }
  }

  return (
    <section id="contact" className="scroll-mt-20 py-16 md:py-24 bg-[var(--brand-black)] text-white">
      <div className="mx-auto max-w-6xl px-4 grid md:grid-cols-2 gap-12">
        <div>
          <SectionHead kicker="Get in touch" title="Let's Talk" dark />
          <p className="mt-6 text-white/70 leading-relaxed">
            Tell me what you need - a shoot, a brand, content for your pages. The more detail the
            better, but even one line is enough to get started.
          </p>
          <ul className="mt-8 space-y-4">
            {s?.contactEmail ? (
              <li className="flex items-center gap-3">
                <span className="h-9 w-9 bg-primary flex items-center justify-center"><Mail className="h-4 w-4" aria-hidden /></span>
                <a href={`mailto:${s.contactEmail}`} className="font-semibold hover:text-primary transition-colors">
                  {s.contactEmail}
                </a>
              </li>
            ) : null}
            {s?.phone ? (
              <li className="flex items-center gap-3">
                <span className="h-9 w-9 bg-primary flex items-center justify-center"><Phone className="h-4 w-4" aria-hidden /></span>
                <a href={`tel:${s.phone}`} className="font-semibold hover:text-primary transition-colors">{s.phone}</a>
              </li>
            ) : null}
            {s?.location ? (
              <li className="flex items-center gap-3">
                <span className="h-9 w-9 bg-primary flex items-center justify-center"><MapPin className="h-4 w-4" aria-hidden /></span>
                <span className="font-semibold">{s.location}</span>
              </li>
            ) : null}
          </ul>
          <div className="mt-8 flex gap-3">
            {socials.map(({ key, icon: Icon, label }) =>
              socialMap[key] ? (
                <a
                  key={key}
                  href={socialMap[key]}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${label} (opens in new tab)`}
                  className="h-10 w-10 border border-white/25 flex items-center justify-center hover:bg-primary hover:border-primary transition-colors"
                >
                  <Icon className="h-4 w-4" aria-hidden />
                </a>
              ) : null
            )}
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4" aria-label="Contact form">
          <div className="space-y-2">
            <Label htmlFor="c-name" className="text-white/80">Name</Label>
            <Input
              id="c-name" required value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Your name" className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="c-email" className="text-white/80">Email</Label>
            <Input
              id="c-email" type="email" required value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@example.com" className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="c-body" className="text-white/80">Message</Label>
            <Textarea
              id="c-body" required rows={5} value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })}
              placeholder="What do you need done?"
              className="bg-white/5 border-white/20 text-white placeholder:text-white/30 focus-visible:ring-primary"
            />
          </div>
          <Button
            type="submit" disabled={sending}
            className="w-full h-12 bg-primary hover:bg-[#B91C1C] text-white font-bold text-base"
          >
            {sending ? "Sending…" : "Send Message"} <Send className="h-4 w-4" aria-hidden />
          </Button>
        </form>
      </div>
    </section>
  );
}

/* ---------------- Footer ---------------- */

export function SiteFooter({ settings }: { settings: PublicSettings | null }) {
  const s = settings;
  return (
    <footer className="bg-[var(--brand-black)] text-white border-t-4 border-primary mt-auto">
      <div className="mx-auto max-w-6xl px-4 py-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <p className="flex items-center gap-2 font-black text-lg uppercase tracking-tight">
            <LogoMark className="h-6 w-6" aria-hidden />
            {s?.siteName || "DeYoung"}
          </p>
          <p className="mt-1 text-sm text-white/50">{s?.tagline || "Bold work. Real results."}</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <a href="#services" className="text-white/60 hover:text-primary transition-colors">Services</a>
          <a href="#gallery" className="text-white/60 hover:text-primary transition-colors">Work</a>
          <a href="#faq" className="text-white/60 hover:text-primary transition-colors">FAQ</a>
          <a href="#privacy" className="text-white/60 hover:text-primary transition-colors">Privacy</a>
          <a href="#admin" className="text-white/30 hover:text-primary transition-colors">Admin</a>
        </nav>
        <p className="text-xs text-white/40 order-last md:order-none">
          © {new Date().getFullYear()} {s?.siteName || "DeYoung"}. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

/* ---------------- How it works (3D diagram) ---------------- */

const STEPS = [
  {
    n: "01",
    icon: PenLine,
    title: "Describe your story",
    body: "Type your idea, pick a length up to 60 seconds and choose 720p or crisp 4K. One prompt is all it takes to start rolling.",
  },
  {
    n: "02",
    icon: Clapperboard,
    title: "DeYoung renders",
    body: "The engine films your scene in a single pass - no stitching fifteen-second clips together and hoping they match.",
  },
  {
    n: "03",
    icon: Download,
    title: "Download & share",
    body: "Your finished film arrives with sound, ready for socials, clients or the big screen. Repeat requests fly out of the cache instantly.",
  },
];

export function HowItWorks() {
  return (
    <section aria-label="How DeYoung works" className="py-16 md:py-24 bg-white overflow-hidden">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHead kicker="How it works" title="From Idea to Film in Three Moves" dark={false} />
        <div className="relative mt-12">
          {/* connector line (the diagram spine) */}
          <div
            className="hidden lg:block absolute top-9 left-[10%] right-[10%] h-[3px] bg-gradient-to-r from-[#DC2626]/10 via-[#DC2626]/60 to-[#DC2626]/10"
            aria-hidden
          />
          <div className="grid md:grid-cols-3 gap-5 dy-scene">
            {STEPS.map((step, i) => (
              <Reveal key={step.n} delay={i * 120}>
                <TiltCard className="h-full relative">
                  <div className="relative h-full bg-white border-2 border-neutral-200 hover:border-primary transition-colors p-6">
                    <div className="flex items-center justify-between">
                      <span className="h-14 w-14 bg-[var(--brand-black)] text-white flex items-center justify-center dy-glow-red">
                        <step.icon className="h-6 w-6" aria-hidden />
                      </span>
                      <span className="text-5xl font-black text-neutral-100 select-none" aria-hidden>
                        {step.n}
                      </span>
                    </div>
                    <h3 className="mt-5 text-xl font-black uppercase tracking-tight">{step.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{step.body}</p>
                    {i < STEPS.length - 1 ? (
                      <ChevronRight
                        className="hidden lg:block absolute -right-[26px] top-8 h-6 w-6 text-primary z-10"
                        aria-hidden
                      />
                    ) : null}
                  </div>
                </TiltCard>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Stats marquee strip ---------------- */

const STRIP_ITEMS = [
  "PRICES JUST WENT UP - LOCK IN NOW",
  "60 SECONDS - ONE PASS",
  "UP TO 4K CINEMATIC",
  "LIVE QUEUE + HONEST ETA",
  "INSTANT CACHE DELIVERY",
  "MOBILE + WEB STUDIO",
  "PAY LOCAL OR INTERNATIONAL",
];

export function StatsStrip() {
  const row = [...STRIP_ITEMS, ...STRIP_ITEMS];
  return (
    <div className="bg-primary text-white overflow-hidden py-3 border-y-4 border-[var(--brand-black)]" aria-hidden>
      <div className="dy-marquee-track">
        {row.map((t, i) => (
          <span key={i} className="mx-6 flex items-center gap-6 text-sm font-black tracking-[0.2em] whitespace-nowrap">
            {t}
            <span className="h-1.5 w-1.5 bg-white/70 rounded-full inline-block" />
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---------------- shared ---------------- */

export function SectionHead({ kicker, title, dark }: { kicker: string; title: string; dark: boolean }) {
  return (
    <div>
      <p className={`text-xs font-black uppercase tracking-[0.3em] ${dark ? "text-primary" : "text-primary"}`}>
        {kicker}
      </p>
      <h2
        className={`mt-2 text-3xl md:text-4xl font-black tracking-tight uppercase ${
          dark ? "text-white" : "text-[var(--brand-black)]"
        }`}
      >
        {title}
      </h2>
      <div className="mt-4 h-1.5 w-20 bg-primary" aria-hidden />
    </div>
  );
}

export type { HomeData };

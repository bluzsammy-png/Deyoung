"use client";

import { useState } from "react";
import Image from "next/image";
import { Check, Copy, Download, Megaphone, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";
import { AdminPanel } from "./admin-content";

/* ---------------- Social flyer kit (Task 59) ----------------
   Fixed campaign assets, served from /public/flyers. Copy is real site
   copy (hero.tsx + plan matrix) — nothing invented. Captions mirror
   download/social/README-captions.txt so every post is one click away. */

type Flyer = {
  file: string;
  title: string;
  platform: string;
  dims: string;
  w: number;
  h: number;
  blurb: string;
  caption: string;
};

const FLYERS: Flyer[] = [
  {
    file: "deyoung-poster-4x5.png",
    title: "Brand Poster",
    platform: "Instagram / Facebook feed",
    dims: "1080 × 1350 (4:5)",
    w: 1080,
    h: 1350,
    blurb: "The flagship. “Bold work. Real results.” + the 60-second one-pass positioning.",
    caption:
      "Bold work. Real results. AI video up to 60 seconds in one pass — where other models stop at 15. Subscribe or book online at deyoungltd.site\n#DeYoung #AIVideo #AIFilm #ContentCreator #VideoMarketing #GenerativeAI",
  },
  {
    file: "deyoung-plans-1x1.png",
    title: "Pricing Flyer",
    platform: "Instagram / Facebook square",
    dims: "1080 × 1080 (1:1)",
    w: 1080,
    h: 1080,
    blurb: "Beginner $12 / Pro $39 / Elite $99 with the founding-prices hook.",
    caption:
      "Founding prices are LIVE: Beginner $12/mo - Pro $39/mo - Elite $99/mo. Up to 60 seconds in one pass. They go up soon — lock yours in.\ndeyoungltd.site\n#DeYoung #AIVideo #FounderDeal #AIStudio #VideoContent",
  },
  {
    file: "deyoung-story-9x16.png",
    title: "Story Promo",
    platform: "Stories / Reels / TikTok / WhatsApp status",
    dims: "1080 × 1920 (9:16)",
    w: 1080,
    h: 1920,
    blurb: "Full-screen vertical: “I typed ONE sentence…” + watch-the-film CTA.",
    caption:
      "I typed ONE sentence... and got a whole video. Watch the 20-second launch film — made entirely in DeYoung. Sound on. deyoungltd.site\n#DeYoung #AIFilm #UGCCreator #MadeWithAI #LaunchFilm",
  },
  {
    file: "deyoung-banner-16x9.png",
    title: "Studio Banner",
    platform: "X (Twitter) / LinkedIn / Facebook link / YouTube community",
    dims: "1600 × 900 (16:9)",
    w: 1600,
    h: 900,
    blurb: "Wide banner for link posts and community tabs.",
    caption:
      "Bold work. Real results. AI video up to 60 seconds in one pass — where other models stop at 15. Subscribe or book online at deyoungltd.site\n#DeYoung #AIVideo #AIFilm #ContentCreator #VideoMarketing #GenerativeAI",
  },
  {
    file: "deyoung-film-4x5.png",
    title: "Launch Film Promo",
    platform: "Instagram / Facebook feed",
    dims: "1080 × 1350 (4:5)",
    w: 1080,
    h: 1350,
    blurb: "Real frame from the shipped 20s launch film with a play chip.",
    caption:
      "I typed ONE sentence... and got a whole video. Watch the 20-second launch film — made entirely in DeYoung. Sound on. deyoungltd.site\n#DeYoung #AIFilm #UGCCreator #MadeWithAI #LaunchFilm",
  },
  {
    file: "deyoung-trust-1x1.png",
    title: "Trust Card",
    platform: "Instagram / Facebook square",
    dims: "1080 × 1080 (1:1)",
    w: 1080,
    h: 1080,
    blurb: "One sentence in, a real film out + the 3 site promises.",
    caption:
      "One sentence in. A real film out. DeYoung turns an idea into a finished video — subscribe or book online at deyoungltd.site\n#DeYoung #AIVideo #AIFilm #MadeWithAI",
  },
];

const ZIP_URL = "/flyers/deyoung-social-flyers.zip";

export function AdminFlyers() {
  const [preview, setPreview] = useState<Flyer | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function copyCaption(f: Flyer) {
    try {
      await navigator.clipboard.writeText(f.caption);
      setCopied(f.file);
      toast.success(`Caption copied — ready to paste for ${f.title}`);
      setTimeout(() => setCopied((c) => (c === f.file ? null : c)), 2500);
    } catch {
      toast.error("Clipboard blocked — select the caption text instead");
    }
  }

  return (
    <div className="space-y-4">
      <AdminPanel
        title={`Social Flyers (${FLYERS.length} pieces)`}
        action={
          <div className="flex gap-2">
            <Button asChild size="sm" className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
              <a href={ZIP_URL} download>
                <Download className="h-4 w-4" aria-hidden /> Download all (ZIP)
              </a>
            </Button>
          </div>
        }
      >
        <div className="flex items-start gap-3 mb-4 bg-neutral-50 border border-neutral-200 p-4">
          <Megaphone className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden />
          <p className="text-sm text-neutral-600">
            The full cinematic social kit in every platform size — brand poster, pricing flyer, story promo,
            wide banner, launch-film promo and trust card. Every line of copy is taken from the live site,
            nothing invented. Tap a flyer to preview it full-size, download exactly what you need, or copy the
            ready-to-post caption with hashtags in one click.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FLYERS.map((f) => (
            <figure key={f.file} className="border-2 border-neutral-200 bg-white flex flex-col">
              <button
                type="button"
                onClick={() => setPreview(f)}
                aria-label={`Preview ${f.title} full-size`}
                className="relative block w-full aspect-[4/5] bg-neutral-950 group cursor-zoom-in"
              >
                <Image
                  src={`/flyers/${f.file}`}
                  alt={`${f.title} — ${f.blurb}`}
                  fill
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="object-contain transition-transform duration-300 group-hover:scale-[1.02]"
                />
                <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                  <span className="bg-white text-neutral-900 text-[11px] font-black uppercase px-3 py-1.5 tracking-wide">
                    Click to preview
                  </span>
                </span>
              </button>

              <figcaption className="p-3 flex flex-col gap-2 grow">
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-black text-sm uppercase tracking-tight">{f.title}</p>
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-neutral-100 text-neutral-600 whitespace-nowrap">
                      {f.dims}
                    </span>
                  </div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-primary mt-0.5">{f.platform}</p>
                  <p className="text-xs text-muted-foreground mt-1">{f.blurb}</p>
                </div>

                <div className="mt-auto flex gap-2 pt-2">
                  <Button asChild size="sm" variant="outline" className="font-bold flex-1">
                    <a href={`/flyers/${f.file}`} download>
                      <Download className="h-3.5 w-3.5" aria-hidden /> PNG
                    </a>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="font-bold flex-1"
                    onClick={() => copyCaption(f)}
                    aria-label={`Copy caption for ${f.title}`}
                  >
                    {copied === f.file ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-green-600" aria-hidden /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" aria-hidden /> Caption
                      </>
                    )}
                  </Button>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>

        <p className="mt-4 text-xs text-muted-foreground flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
          Tip: pair each flyer with its caption — the hashtag block is included. The ZIP contains all 6 PNGs plus
          the captions file.
        </p>
      </AdminPanel>

      <Dialog open={preview !== null} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-4xl bg-neutral-950 border-neutral-800 p-3 sm:p-4">
          <div className="sr-only">
            <DialogTitle>{preview?.title} — full preview</DialogTitle>
            <DialogDescription>{preview ? `${preview.dims} — ${preview.platform}` : ""}</DialogDescription>
          </div>
          {preview && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-center bg-neutral-950 rounded-sm overflow-hidden min-h-[40vh]">
                <Image
                  src={`/flyers/${preview.file}`}
                  alt={`${preview.title} full preview`}
                  width={preview.w}
                  height={preview.h}
                  className="max-h-[70vh] w-auto max-w-full h-auto object-contain"
                  priority
                />
              </div>
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="font-black uppercase text-white text-sm tracking-tight">{preview.title}</p>
                  <p className="text-xs text-neutral-400 font-semibold">
                    {preview.dims} · {preview.platform}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button asChild size="sm" className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
                    <a href={`/flyers/${preview.file}`} download>
                      <Download className="h-4 w-4" aria-hidden /> Download PNG
                    </a>
                  </Button>
                  <Button size="sm" variant="outline" className="font-bold" onClick={() => copyCaption(preview)}>
                    {copied === preview.file ? (
                      <>
                        <Check className="h-4 w-4 text-green-600" aria-hidden /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" aria-hidden /> Copy caption
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Seed DeYoung demo content + owner account + settings.
 * Run: bun scripts/seed.ts
 */
import { PrismaClient } from "@prisma/client";
import crypto from "crypto";
import fs from "fs";
import path from "path";

const prisma = new PrismaClient();

function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt$${salt}$${hash}`;
}

async function main() {
  // ---- owner account ----
  // W0 fix (§F.1): never seed a public default password. Bootstrap password comes
  // from ADMIN_BOOTSTRAP_PASSWORD env (>=10 chars) or is generated + printed once.
  const adminCount = await prisma.admin.count();
  if (adminCount === 0) {
    const fromEnv = process.env.ADMIN_BOOTSTRAP_PASSWORD;
    const password = fromEnv && fromEnv.length >= 10 ? fromEnv : crypto.randomBytes(12).toString("base64url");
    await prisma.admin.create({
      data: { email: "admin@deyoung.site", passwordHash: hashPassword(password) },
    });
    console.log(`seed: admin admin@deyoung.site / ${password} (change it in Security immediately)`);
  }

  // ---- settings ----
  const oldSubtitle =
    "Photography, design and digital services that get you noticed — booked online, delivered fast, paid your way (local or international).";
  const newSubtitle =
    "AI video generation up to 60 seconds in one pass — where other models stop at 15. Plus bold creative services. Subscribe or book online, paid your way (local or international).";
  const oldMeta =
    "DeYoung — bold creative work: photography, design and digital services. Book online, pay locally or internationally.";
  const newMeta =
    "DeYoung — AI video generation up to 60 seconds in one pass, plus bold creative services. Subscribe or book online, pay locally or internationally.";

  const existingSettings = await prisma.settings.findUnique({ where: { id: "main" } });
  await prisma.settings.upsert({
    where: { id: "main" },
    // Refresh stale default copy to the video positioning, but never overwrite owner edits.
    update: {
      ...(existingSettings?.heroSubtitle === oldSubtitle ? { heroSubtitle: newSubtitle } : {}),
      ...(existingSettings?.metaDescription === oldMeta ? { metaDescription: newMeta } : {}),
    },
    create: {
      id: "main",
      siteName: "DeYoung",
      tagline: "Bold work. Real results.",
      heroTitle: "DEYOUNG",
      heroSubtitle: newSubtitle,
      aboutTitle: "About DeYoung",
      aboutBody:
        "I'm DeYoung — a creative professional who keeps things simple: sharp work, honest pricing and fast delivery. Every piece in the gallery below is real work for real people. Pick a service, tell me what you need, and consider it handled. I reply within 24 hours — usually much faster.",
      ownerName: "DeYoung",
      ownerTitle: "Creative Professional",
      ownerPhotoUrl: "/img/avatar-default.png",
      contactEmail: "hello@deyoung.site",
      phone: "",
      whatsapp: "",
      location: "",
      responseTime: "Replies within 24 hours — usually much faster.",
      currency: "USD",
      paymentProvider: "manual",
      paymentInstructions:
        "Pay via bank transfer or mobile money using the details below, then send your receipt on WhatsApp. Your booking is confirmed as soon as payment is received.",
      bankDetails: "Bank: —\nAccount name: —\nAccount number: —\nMobile money: —",
      socialJson: JSON.stringify({ instagram: "", tiktok: "", x: "", facebook: "", youtube: "" }),
      metaDescription: newMeta,
      gpuMinutesDaily: 240,
    },
  });

  // ---- subscription plans (Beginner / Pro / Elite) ----
  const planDefaults = [
    {
      code: "beginner",
      name: "Beginner",
      blurb: "Taste the engine. Short clips, small price.",
      priceMonthly: 12,
      compareAtPrice: 18,
      maxVideosMonth: 4,
      maxSecondsVideo: 15,
      maxResolution: "720p",
      watermark: true,
      concurrentJobs: 1,
      queuePriority: 0,
      commercial: false,
      audio: false,
      featuresJson: JSON.stringify([
        { label: "4 videos per month", included: true },
        { label: "Up to 15 seconds per video", included: true },
        { label: "720p HD", included: true },
        { label: "DeYoung watermark", included: true },
        { label: "Personal use license", included: true },
        { label: "60-second single-pass videos", included: false },
        { label: "1080p Full HD", included: false },
        { label: "No watermark", included: false },
        { label: "Priority queue", included: false },
        { label: "Commercial license", included: false },
      ]),
      sortOrder: 1,
    },
    {
      code: "pro",
      name: "Pro",
      blurb: "The full engine — 60 seconds at a go, clean and in HD.",
      priceMonthly: 39,
      compareAtPrice: 59,
      maxVideosMonth: 20,
      maxSecondsVideo: 60,
      maxResolution: "1080p",
      watermark: false,
      concurrentJobs: 2,
      queuePriority: 1,
      commercial: true,
      audio: true,
      featuresJson: JSON.stringify([
        { label: "20 videos per month", included: true },
        { label: "Up to 60 seconds in one pass", included: true },
        { label: "1080p Full HD", included: true },
        { label: "No watermark", included: true },
        { label: "Audio included", included: true },
        { label: "Commercial license", included: true },
        { label: "Standard queue", included: true },
        { label: "2 videos rendering at once", included: true },
        { label: "Priority queue", included: false },
        { label: "Multi-scene batches", included: false },
      ]),
      sortOrder: 2,
    },
    {
      code: "elite",
      name: "Elite",
      blurb: "For creators and agencies who ship volume.",
      priceMonthly: 99,
      compareAtPrice: 149,
      maxVideosMonth: 60,
      maxSecondsVideo: 60,
      maxResolution: "1080p",
      watermark: false,
      concurrentJobs: 4,
      queuePriority: 2,
      commercial: true,
      audio: true,
      featuresJson: JSON.stringify([
        { label: "60 videos per month", included: true },
        { label: "Up to 60 seconds in one pass", included: true },
        { label: "Multi-scene batches (stitch several 60s scenes)", included: true },
        { label: "1080p Full HD", included: true },
        { label: "No watermark", included: true },
        { label: "Audio included", included: true },
        { label: "Priority queue — rendered first", included: true },
        { label: "4 videos rendering at once", included: true },
        { label: "Commercial license", included: true },
        { label: "Source files & early features", included: true },
      ]),
      sortOrder: 3,
    },
  ];

  for (const p of planDefaults) {
    await prisma.plan.upsert({
      where: { code: p.code },
      update: {},
      create: p,
    });
  }
  console.log("seed: 3 plans (beginner / pro / elite)");

  // ---- services ----
  const svcCount = await prisma.service.count();
  if (svcCount === 0) {
    await prisma.service.createMany({
      data: [
        {
          title: "Portrait Session",
          description:
            "A full personal portrait session — 15 edited photos, studio or location, delivered in 72 hours.",
          price: 65,
          compareAtPrice: 95,
          duration: "1–2 hours",
          sortOrder: 1,
        },
        {
          title: "Brand Design Pack",
          description:
            "Logo, colour system and 3 social templates that make your business look like a serious brand.",
          price: 150,
          compareAtPrice: 210,
          duration: "3–5 days",
          sortOrder: 2,
        },
        {
          title: "Event Coverage",
          description:
            "Birthdays, weddings, launches — 40+ edited photos and a highlight reel your people will actually share.",
          price: 250,
          compareAtPrice: 350,
          duration: "Full day",
          sortOrder: 3,
        },
        {
          title: "Content Day",
          description:
            "One day, one shot list: 30 photos + 5 short videos for your socials, planned and delivered.",
          price: 185,
          compareAtPrice: 260,
          duration: "4–6 hours",
          sortOrder: 4,
        },
      ],
    });
    console.log("seed: 4 services");
  }

  // ---- gallery photos ----
  const photoCount = await prisma.photo.count();
  if (photoCount === 0) {
    await prisma.photo.createMany({
      data: [
        { title: "Portrait work", alt: "Studio portrait sample in black and red", url: "/img/gallery-1.png", category: "work", sortOrder: 1 },
        { title: "Brand identity", alt: "Brand design sample with white and red layout", url: "/img/gallery-2.png", category: "work", sortOrder: 2 },
        { title: "Editorial shoot", alt: "Editorial photo sample, dark tones with red accent", url: "/img/gallery-3.png", category: "work", sortOrder: 3 },
        { title: "Event coverage", alt: "Event photo sample with red and white styling", url: "/img/gallery-4.png", category: "work", sortOrder: 4 },
        { title: "Studio session", alt: "Studio work sample in white and black", url: "/img/gallery-5.png", category: "work", sortOrder: 5 },
        { title: "Commercial campaign", alt: "Commercial campaign sample, black with red accents", url: "/img/gallery-6.png", category: "work", sortOrder: 6 },
      ],
    });
    console.log("seed: 6 photos");
  }

  // ---- W2: expanded premium gallery (AI film stills + style lab) ----
  const aiFilmCount = await prisma.photo.count({ where: { category: { in: ["ai-film", "style-lab"] } } });
  if (aiFilmCount === 0) {
    await prisma.photo.createMany({
      data: [
        { title: "The 60s film", alt: "DeYoung AI film poster — 60 seconds in one pass", url: "/img/film-poster.jpg", category: "ai-film", sortOrder: 10 },
        { title: "Cartoon lead", alt: "AI-generated cartoon boy character in red lighting", url: "/showreel/style-cartoon.png", category: "ai-film", sortOrder: 11 },
        { title: "Anime cut", alt: "AI anime style frame from the film pipeline", url: "/showreel/style-anime.png", category: "ai-film", sortOrder: 12 },
        { title: "Real-toon hybrid", alt: "Ultra-realistic AI character frame", url: "/showreel/style-real.png", category: "ai-film", sortOrder: 13 },
        { title: "Kids show frame", alt: "Playful kids-cartoon AI frame", url: "/showreel/style-kids.png", category: "ai-film", sortOrder: 14 },
        { title: "Stick-man runner", alt: "Hand-drawn stick-man animation test", url: "/showreel/style-stickman.png", category: "style-lab", sortOrder: 15 },
        { title: "Split style study", alt: "Side-by-side AI style comparison frame", url: "/showreel/style-split.png", category: "style-lab", sortOrder: 16 },
        { title: "The lineup", alt: "Full DeYoung character lineup", url: "/showreel/style-lineup.png", category: "style-lab", sortOrder: 17 },
        { title: "Brand systems", alt: "Brand design work sample", url: "/img/work/brand.png", category: "work", sortOrder: 18 },
        { title: "Commercial set", alt: "Commercial production sample", url: "/img/work/commercial.png", category: "work", sortOrder: 19 },
        { title: "Editorial frame", alt: "Editorial shoot sample", url: "/img/work/editorial.png", category: "work", sortOrder: 20 },
        { title: "Live event", alt: "Event coverage sample", url: "/img/work/event.png", category: "work", sortOrder: 21 },
        { title: "Portrait series", alt: "Portrait session sample", url: "/img/work/portrait.png", category: "work", sortOrder: 22 },
        { title: "Studio session", alt: "Studio photography sample", url: "/img/work/studio.png", category: "work", sortOrder: 23 },
      ],
    });
    console.log("seed: 14 gallery works added (AI film + style lab + studio)");
  }

  // ---- W2: owner admin seat (deyoungsltd@gmail.com) — passwordless via Google ----
  const ownerAdmin = await prisma.admin.findUnique({ where: { email: "deyoungsltd@gmail.com" } });
  if (!ownerAdmin) {
    const env = process.env.ADMIN_BOOTSTRAP_PASSWORD;
    const password = env && env.length >= 10 ? env : crypto.randomBytes(12).toString("base64url");
    await prisma.admin.create({
      data: { email: "deyoungsltd@gmail.com", passwordHash: hashPassword(password) },
    });
    if (!env) console.log("seed: owner admin deyoungsltd@gmail.com / (one-time password in log)");
    else console.log("seed: owner admin deyoungsltd@gmail.com created (bootstrap password)");
  }

  // ---- testimonials ----
  // HONESTY RULE (Master Upgrade Instruction §28, Task 62): the site ships with ZERO
  // fabricated reviews. Real testimonials are entered by the owner in Admin →
  // Reviews & FAQ only, after real client work. The testimonials section renders
  // nothing while the list is empty (Testimonials returns null).
  console.log("seed: testimonials skipped by design (no fabricated reviews)");

  // ---- FAQ ----
  if ((await prisma.faq.count()) === 0) {
    await prisma.faq.createMany({
      data: [
        {
          question: "How do I book?",
          answer:
            "Pick a service, hit Book Now, fill in your details and choose how you want to pay. You get a confirmation right away and a reply from me within 24 hours.",
          sortOrder: 1,
        },
        {
          question: "How do I pay? Does it work in my country?",
          answer:
            "Yes — payment works locally and internationally. You can pay by bank transfer or mobile money (local), or by card / PayPal / Paystack / Flutterwave (international) depending on the option shown at checkout.",
          sortOrder: 2,
        },
        {
          question: "How fast is delivery?",
          answer:
            "Most orders are delivered in 48–72 hours. Bigger projects (brand packs, event coverage) take 3–5 days. You always get the exact timeline before you pay.",
          sortOrder: 3,
        },
        {
          question: "Can I change or cancel a booking?",
          answer:
            "Yes. Contact me at least 24 hours before the session and we reschedule free of charge, or cancel for a full refund if work has not started.",
          sortOrder: 4,
        },
        {
          question: "Do I get the raw files?",
          answer:
            "You get all edited files in high resolution with full personal-use rights. Raw files are available on request for event coverage.",
          sortOrder: 5,
        },
        {
          question: "Is this site secure?",
          answer:
            "Yes — your booking details are stored privately, only the site owner can access the admin panel, and card payments are handled by the payment provider (no card details ever touch this site).",
          sortOrder: 6,
        },
      ],
    });
    console.log("seed: 6 FAQs");
  }

  // ---- AI video FAQs (added separately so existing installs also get them) ----
  const videoFaqs = [
    {
      question: "How long can one video be?",
      answer:
        "Up to 60 seconds in a single pass on Pro and Elite — that is the DeYoung difference, where most other tools stop at 15 seconds. Beginner plans render up to 15-second clips, and Elite can stitch several 60-second scenes into a batch.",
      sortOrder: 7,
    },
    {
      question: "How does the video queue work?",
      answer:
        "Videos are rendered in a fair queue: Elite first, then Pro, then Beginner. You submit your prompt, see your queue position immediately, and the finished video is delivered to your status link — usually within 24–72 hours depending on demand.",
      sortOrder: 8,
    },
  ];
  for (const f of videoFaqs) {
    const exists = await prisma.faq.findFirst({ where: { question: f.question } });
    if (!exists) await prisma.faq.create({ data: f });
  }
  console.log("seed: video FAQs present");

  // ---- W2.2 Premiere Wall (added separately so existing installs also get it) ----
  // Honest launch content: three real DeYoung works that already ship on the
  // site (the produced web film + two showreel clips). No fake durations, no
  // fake entries — the fleet's delivered renders join via the admin panel.
  const premieres = [
    {
      title: "The DeYoung Film",
      logline: "The short that started the studio — written, rendered and cut by the DeYoung pipeline.",
      category: "ai-film",
      videoUrl: "/video/deyoung-film-web.mp4",
      posterUrl: "/img/film-poster.jpg",
      featured: true,
      durationSec: 0,
    },
    {
      title: "Cartoon Gag — Reel Cut",
      logline: "A stylized gag rendered in the cartoon look, straight from the showreel.",
      category: "style-lab",
      videoUrl: "/showreel/clip-cartoon.mp4",
      posterUrl: "/showreel/style-cartoon.png",
      featured: false,
      durationSec: 0,
    },
    {
      title: "Doors, Split Screen",
      logline: "Style Lab experiment: one beat, two looks, split down the middle.",
      category: "style-lab",
      videoUrl: "/showreel/clip-doors.mp4",
      posterUrl: "/showreel/style-split.png",
      featured: false,
      durationSec: 0,
    },
  ];
  for (const p of premieres) {
    const exists = await prisma.premiere.findFirst({ where: { title: p.title } });
    if (!exists) {
      await prisma.premiere.create({ data: { ...p, status: "published", source: "admin" } });
    }
  }
  console.log("seed: premieres present");

  console.log("seed done.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());

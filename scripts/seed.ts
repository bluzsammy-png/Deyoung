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
  const adminCount = await prisma.admin.count();
  if (adminCount === 0) {
    await prisma.admin.create({
      data: { email: "admin@deyoung.site", passwordHash: hashPassword("deyoung123") },
    });
    console.log("seed: admin admin@deyoung.site / deyoung123");
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
      priceMonthly: 18,
      compareAtPrice: 25,
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
      priceMonthly: 59,
      compareAtPrice: 85,
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
      priceMonthly: 149,
      compareAtPrice: 199,
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
          price: 95,
          compareAtPrice: 135,
          duration: "1–2 hours",
          sortOrder: 1,
        },
        {
          title: "Brand Design Pack",
          description:
            "Logo, colour system and 3 social templates that make your business look like a serious brand.",
          price: 210,
          compareAtPrice: 299,
          duration: "3–5 days",
          sortOrder: 2,
        },
        {
          title: "Event Coverage",
          description:
            "Birthdays, weddings, launches — 40+ edited photos and a highlight reel your people will actually share.",
          price: 350,
          compareAtPrice: 499,
          duration: "Full day",
          sortOrder: 3,
        },
        {
          title: "Content Day",
          description:
            "One day, one shot list: 30 photos + 5 short videos for your socials, planned and delivered.",
          price: 260,
          compareAtPrice: 365,
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
        { title: "Portrait work", alt: "Studio portrait sample in black and red", url: "/img/gallery-1.png", sortOrder: 1 },
        { title: "Brand identity", alt: "Brand design sample with white and red layout", url: "/img/gallery-2.png", sortOrder: 2 },
        { title: "Editorial shoot", alt: "Editorial photo sample, dark tones with red accent", url: "/img/gallery-3.png", sortOrder: 3 },
        { title: "Event coverage", alt: "Event photo sample with red and white styling", url: "/img/gallery-4.png", sortOrder: 4 },
        { title: "Studio session", alt: "Studio work sample in white and black", url: "/img/gallery-5.png", sortOrder: 5 },
        { title: "Commercial campaign", alt: "Commercial campaign sample, black with red accents", url: "/img/gallery-6.png", sortOrder: 6 },
      ],
    });
    console.log("seed: 6 photos");
  }

  // ---- testimonials ----
  if ((await prisma.testimonial.count()) === 0) {
    await prisma.testimonial.createMany({
      data: [
        {
          name: "Amara O.",
          role: "Boutique owner",
          quote:
            "Booked a content day, had 35 photos and 5 videos back before the weekend. My Instagram has never looked this good.",
          rating: 5,
          sortOrder: 1,
        },
        {
          name: "Kwame B.",
          role: "Music artist",
          quote:
            "The brand pack changed everything — people take my pages seriously now. Fast, clean, no stories.",
          rating: 5,
          sortOrder: 2,
        },
        {
          name: "Tessa M.",
          role: "Event planner",
          quote:
            "Covered a wedding for 200 guests and still delivered the highlight reel in two days. Book with confidence.",
          rating: 5,
          sortOrder: 3,
        },
      ],
    });
    console.log("seed: 3 testimonials");
  }

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

  console.log("seed done.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());

// One-off (Sept 2026): THIRD price rise + real portfolio works on the LIVE Supabase DB.
//
//  A) Photos: replace the 6 generic category tiles with 18 real work samples
//     (3 per category: Portrait, Brand, Editorial, Event, Studio, Commercial).
//     Title format: "<Category> — <description>" (category = part before the em dash,
//     parsed by the gallery UI for its category tabs).
//  B) Prices: plans 18/59/149 -> 24/79/199, services 95/210/350/260 -> 120/265/450/330,
//     with new, higher compare-at prices so the urgency stays honest.
//
// Workflow:
//   1) npx prisma generate --schema prisma/schema.postgres.prisma
//   2) DATABASE_URL='<supabase tx pooler url>' node scripts/works_and_pricing3.mjs
//   3) npx prisma generate   (restore the sqlite client for local dev)
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const WORKS = [
  // Portrait
  { title: 'Portrait — Red studio headshot',      url: '/works/portrait-01.jpg', alt: 'Studio headshot with braids on a red backdrop' },
  { title: 'Portrait — Monochrome suit',          url: '/works/portrait-02.jpg', alt: 'Black and white studio portrait in a tailored suit' },
  { title: 'Portrait — Golden hour ankara',       url: '/works/portrait-03.jpg', alt: 'Golden hour portrait in colorful ankara fashion' },
  // Brand
  { title: 'Brand — Shea butter campaign',        url: '/works/brand-01.jpg',    alt: 'Skincare jar product shot for a brand campaign' },
  { title: 'Brand — Stationery identity',         url: '/works/brand-02.jpg',    alt: 'Brand identity stationery flat lay in red, black and white' },
  { title: 'Brand — Cafe lifestyle',              url: '/works/brand-03.jpg',    alt: 'Barista pouring espresso, lifestyle brand shoot' },
  // Editorial
  { title: 'Editorial — Concrete avant-garde',    url: '/works/editorial-01.jpg', alt: 'Avant-garde red and black fashion editorial' },
  { title: 'Editorial — Rooftop agbada',          url: '/works/editorial-02.jpg', alt: 'Rooftop editorial of a model in flowing agbada at dusk' },
  { title: 'Editorial — Red gel shadows',         url: '/works/editorial-03.jpg', alt: 'Editorial portrait with red gel lighting and shadows' },
  // Event
  { title: 'Event — Traditional wedding entrance', url: '/works/event-01.jpg',    alt: 'Traditional wedding entrance with celebrating guests' },
  { title: 'Event — Corporate award night',       url: '/works/event-02.jpg',    alt: 'Award night stage moment under bright lights' },
  { title: 'Event — Sparkler cake moment',        url: '/works/event-03.jpg',    alt: 'Birthday sparkler cake with cheering friends' },
  // Studio
  { title: 'Studio — Cinema set BTS',             url: '/works/studio-01.jpg',   alt: 'Behind the scenes of a cinema camera set' },
  { title: 'Studio — Podcast session',            url: '/works/studio-02.jpg',   alt: 'Two podcast hosts recording in a red-lit studio' },
  { title: 'Studio — Backdrop setup',             url: '/works/studio-03.jpg',   alt: 'Photography studio with seamless backdrop and lighting rigs' },
  // Commercial
  { title: 'Commercial — Bottle splash',          url: '/works/commercial-01.jpg', alt: 'Soda bottle splash on a bold red background' },
  { title: 'Commercial — Family dinner spot',     url: '/works/commercial-02.jpg', alt: 'Cinematic family dinner advertising shot' },
  { title: 'Commercial — Sneaker hero',           url: '/works/commercial-03.jpg', alt: 'Sneaker hero shot over a red gradient' },
];

const PLANS = [
  { code: 'beginner', priceMonthly: 24,  compareAtPrice: 35 },
  { code: 'pro',      priceMonthly: 79,  compareAtPrice: 115 },
  { code: 'elite',    priceMonthly: 199, compareAtPrice: 279 },
];

const SERVICES = [
  { title: 'Portrait Session',   price: 120, compareAtPrice: 175 },
  { title: 'Brand Design Pack',  price: 265, compareAtPrice: 385 },
  { title: 'Event Coverage',     price: 450, compareAtPrice: 650 },
  { title: 'Content Day',        price: 330, compareAtPrice: 470 },
];

async function main() {
  // ---- A) photos: wipe the 6 generic tiles, insert the 18 real works ----
  const before = await prisma.photo.findMany({ orderBy: { sortOrder: 'asc' }, select: { id: true, title: true, url: true } });
  console.log(`photos before: ${before.length}`);
  for (const p of before) console.log(`  - ${p.title} -> ${p.url}`);

  await prisma.photo.deleteMany({});
  let i = 0;
  for (const w of WORKS) {
    await prisma.photo.create({ data: { ...w, sortOrder: i++ } });
  }
  const after = await prisma.photo.findMany({ orderBy: { sortOrder: 'asc' }, select: { title: true, url: true } });
  console.log(`photos after: ${after.length} (works seeded)`);

  // ---- B) third price rise ----
  for (const p of PLANS) {
    const r = await prisma.plan.update({ where: { code: p.code }, data: { priceMonthly: p.priceMonthly, compareAtPrice: p.compareAtPrice } });
    console.log(`plan ${r.code}: $${r.priceMonthly}/mo (was $${r.compareAtPrice})`);
  }
  for (const s of SERVICES) {
    const found = await prisma.service.findFirst({ where: { title: s.title } });
    if (!found) { console.error(`service not found: ${s.title}`); continue; }
    const r = await prisma.service.update({ where: { id: found.id }, data: { price: s.price, compareAtPrice: s.compareAtPrice } });
    console.log(`service ${r.title}: $${r.price} (was $${r.compareAtPrice})`);
  }

  const plans = await prisma.plan.findMany({ orderBy: { sortOrder: 'asc' }, select: { code: true, priceMonthly: true, compareAtPrice: true } });
  console.log('verify plans:', JSON.stringify(plans));
  const svcs = await prisma.service.findMany({ orderBy: { sortOrder: 'asc' }, select: { title: true, price: true, compareAtPrice: true } });
  console.log('verify services:', JSON.stringify(svcs));
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());

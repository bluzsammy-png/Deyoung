// One-off (Sept 2026): second price rise — the founding window promised in the
// launch banners is now closed. Raises plans + services on the LIVE Supabase DB
// and sets new, higher compare-at ("was") prices so the urgency stays honest.
//
// Workflow (same as the first rise):
//   1) npx prisma generate --schema prisma/schema.postgres.prisma
//   2) DATABASE_URL='<supabase tx pooler url>' node scripts/apply_pricing2.mjs
//   3) npx prisma generate   (restore the sqlite client for local dev)
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const PLANS = [
  { code: 'beginner', priceMonthly: 18, compareAtPrice: 25 },
  { code: 'pro', priceMonthly: 59, compareAtPrice: 85 },
  { code: 'elite', priceMonthly: 149, compareAtPrice: 199 },
];

const SERVICES = [
  { title: 'Portrait Session', price: 95, compareAtPrice: 135 },
  { title: 'Brand Design Pack', price: 210, compareAtPrice: 299 },
  { title: 'Event Coverage', price: 350, compareAtPrice: 499 },
  { title: 'Content Day', price: 260, compareAtPrice: 365 },
];

async function main() {
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

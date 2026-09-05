// One-off: raise prices + set compare-at ("slashed") prices on the LIVE Supabase DB.
// Usage: DATABASE_URL=... node scripts/apply_pricing.mjs
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const PLANS = [
  { code: 'beginner', priceMonthly: 12, compareAtPrice: 18 },
  { code: 'pro', priceMonthly: 39, compareAtPrice: 59 },
  { code: 'elite', priceMonthly: 99, compareAtPrice: 149 },
];

const SERVICES = [
  { title: 'Portrait Session', price: 65, compareAtPrice: 95 },
  { title: 'Brand Design Pack', price: 150, compareAtPrice: 210 },
  { title: 'Event Coverage', price: 250, compareAtPrice: 350 },
  { title: 'Content Day', price: 185, compareAtPrice: 260 },
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

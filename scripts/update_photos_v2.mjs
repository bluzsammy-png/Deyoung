// One-off: point the 6 "The Work Speaks" category tiles at the new real-work
// images (v2-*.png). Lists current rows first, then updates url/alt per title.
// Run:  DATABASE_URL='<url>' node scripts/update_photos_v2.mjs
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const MAP = [
  { match: /portrait/i, url: '/img/work/v2-portrait.png', alt: 'Portrait session work by DeYoung — dramatic red-gel studio portrait' },
  { match: /brand/i,    url: '/img/work/v2-brand.png',    alt: 'Brand campaign work by DeYoung — red jacket lookbook frame' },
  { match: /editorial/i,url: '/img/work/v2-editorial.png',alt: 'Editorial work by DeYoung — high-fashion red sculptural outfit' },
  { match: /event/i,    url: '/img/work/v2-event.png',    alt: 'Event coverage work by DeYoung — packed concert, red and white beams' },
  { match: /studio/i,   url: '/img/work/v2-studio.png',   alt: 'Studio production work by DeYoung — cinema camera behind the scenes' },
  { match: /commercial/i,url: '/img/work/v2-commercial.png',alt: 'Commercial work by DeYoung — red perfume key visual with splash' },
];

async function main() {
  const photos = await prisma.photo.findMany({ orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }] });
  console.log(`found ${photos.length} photos:`);
  for (const p of photos) console.log(` - [${p.id}] "${p.title}" -> ${p.url}`);

  for (const p of photos) {
    const m = MAP.find((m) => m.match.test(p.title));
    if (!m) { console.log(`no match for "${p.title}", skipping`); continue; }
    if (p.url === m.url) { console.log(`"${p.title}" already -> ${m.url}`); continue; }
    const r = await prisma.photo.update({ where: { id: p.id }, data: { url: m.url, alt: m.alt } });
    console.log(`updated "${r.title}" -> ${r.url}`);
  }
}
main().finally(() => prisma.$disconnect());

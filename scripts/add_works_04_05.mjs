// One-off: add works 04 & 05 per category to LIVE Supabase (appends after existing 18).
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const WORKS = [
  { title: 'Portrait — Corporate headshot',        url: '/works/portrait-04.jpg', alt: 'Corporate headshot with glasses on grey backdrop' },
  { title: 'Portrait — Artist at rest',            url: '/works/portrait-05.jpg', alt: 'Creative portrait of an artist with paint-stained hands' },
  { title: 'Brand — Coffee packaging',             url: '/works/brand-04.jpg',    alt: 'Premium coffee bag packaging shoot' },
  { title: 'Brand — Rebrand reveal',               url: '/works/brand-05.jpg',    alt: 'Rebrand reveal with bag, tote and poster' },
  { title: 'Editorial — Monochrome duo',           url: '/works/editorial-04.jpg', alt: 'Two models in monochrome with one red accent' },
  { title: 'Editorial — Lagos blue hour',          url: '/works/editorial-05.jpg', alt: 'Street style editorial crossing a Lagos street at blue hour' },
  { title: 'Event — Naming ceremony',              url: '/works/event-04.jpg',    alt: 'Outdoor naming ceremony celebration' },
  { title: 'Event — Concert lights',               url: '/works/event-05.jpg',    alt: 'Concert crowd under red stage lights' },
  { title: 'Studio — Green screen BTS',            url: '/works/studio-04.jpg',   alt: 'Green screen studio behind the scenes' },
  { title: 'Studio — Voice booth',                 url: '/works/studio-05.jpg',   alt: 'Voice actor recording in a booth' },
  { title: 'Commercial — Perfume silk',            url: '/works/commercial-04.jpg', alt: 'Perfume bottle with flowing silk on red' },
  { title: 'Commercial — Burger steam',            url: '/works/commercial-05.jpg', alt: 'Burger with steam and flying ingredients' },
];

async function main() {
  const max = await prisma.photo.aggregate({ _max: { sortOrder: true } });
  let i = (max._max.sortOrder ?? -1) + 1;
  for (const w of WORKS) {
    const exists = await prisma.photo.findFirst({ where: { url: w.url } });
    if (exists) { console.log('skip (exists):', w.url); continue; }
    await prisma.photo.create({ data: { ...w, sortOrder: i++ } });
    console.log('added:', w.title);
  }
  const n = await prisma.photo.count();
  console.log('total photos now:', n);
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());

// One-off: cache-bust the 6 gallery photo URLs after replacing the images.
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const photos = await prisma.photo.findMany({ orderBy: { sortOrder: 'asc' } });
  for (const p of photos) {
    if (!p.url.startsWith('/img/gallery-')) continue;
    const base = p.url.split('?')[0];
    const url = `${base}?v=2`;
    await prisma.photo.update({ where: { id: p.id }, data: { url } });
    console.log(`${p.title}: ${p.url} -> ${url}`);
  }
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());

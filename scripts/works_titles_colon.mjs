// Migrate works titles from "Category - description" (was an em dash) to
// "Category: description" so the gallery parser (title.split(":")) works.
import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();
const rows = await db.photo.findMany({ select: { id: true, title: true } });
let n = 0;
for (const r of rows) {
  const m = r.title.match(/^(Portrait|Brand|Editorial|Event|Studio|Commercial)\s*[\u2014\u2013-]\s*(.+)$/);
  if (!m) continue;
  await db.photo.update({ where: { id: r.id }, data: { title: `${m[1]}: ${m[2]}` } });
  n++;
}
console.log(`updated ${n}/${rows.length} photo titles`);
await db.$disconnect();

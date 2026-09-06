/** Count rows per model in the target schema. Usage:
 *   DATABASE_URL='postgresql://...?schema=deyoung' npx tsx scripts/w1_count_rows.ts
 * Credentials come from workers/secrets/supabase.json or env — never hardcoded. */
import { PrismaClient } from "../prisma/pg-client-tmp";

const url = process.env.DATABASE_URL;
if (!url || !url.includes("schema=")) {
  throw new Error("Set DATABASE_URL (pooler URL with ?schema=...). Values live in workers/secrets/supabase.json.");
}

const p = new PrismaClient({ datasources: { db: { url } } });
async function main() {
  const [svc, photo, faq, plan, tst, settings, admin] = await Promise.all([
    p.service.count(),
    p.photo.count(),
    p.faq.count(),
    p.plan.count(),
    p.testimonial.count(),
    p.settings.count(),
    p.admin.count(),
  ]);
  console.log({ svc, photo, faq, plan, tst, settings, admin });
  await p.$disconnect();
}
main().catch((e) => {
  console.error("FAIL:", e.message.slice(0, 300));
  process.exit(1);
});

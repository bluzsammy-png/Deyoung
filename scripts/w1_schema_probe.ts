/** Probe model row-counts across Postgres schemas. Usage:
 *   DATABASE_URL='postgresql://user:pass@host:5432/postgres' npx tsx scripts/w1_schema_probe.ts
 * Probes DATABASE_URL's schema and `public`. Credentials live in
 * workers/secrets/supabase.json — never hardcoded here. */
import { PrismaClient } from "../prisma/pg-client-tmp";

const base = process.env.DATABASE_URL ?? "";
if (!base) {
  throw new Error("Set DATABASE_URL (no ?schema= needed; base URL). Values live in workers/secrets/supabase.json.");
}

async function probe(schema: string) {
  const url = `${base}?schema=${schema}`;
  const p = new PrismaClient({ datasources: { db: { url } } });
  try {
    const out: any = { schema };
    for (const m of ["settings", "service", "photo", "faq", "plan", "testimonial", "rateLimit", "admin", "videoRequest", "asset"] as const) {
      try {
        out[m] = await (p as any)[m].count();
      } catch (e: any) {
        out[m] = "ERR";
      }
    }
    const s = await p.settings.findUnique({ where: { id: "main" } }).catch(() => null);
    out.siteName = s?.siteName ?? null;
    console.log(JSON.stringify(out));
  } finally {
    await p.$disconnect();
  }
}

async function main() {
  if (!base) {
    console.error("FAIL: set DATABASE_URL (env-driven diagnostic, no defaults)");
    process.exit(1);
  }
  const current = new URL(base).searchParams.get("schema") || "public";
  await probe(current);
  if (current !== "public") await probe("public");
}
main().catch((e) => { console.error("FAIL:", e.message.slice(0, 200)); process.exit(1); });

import { PrismaClient } from "@prisma/client";

// C-6 fix: credentials live only in env / the vault — never in this file.
const TX_URL = (process.env.DATABASE_URL || "").replace(":5432", ":6543");
if (!TX_URL || !TX_URL.includes("://")) {
  throw new Error("Set DATABASE_URL (session-pooler URL with ?schema=deyoung). Values live in workers/secrets/supabase.json.");
}
const db = new PrismaClient({ datasources: { db: { url: TX_URL + (TX_URL.includes("?") ? "&" : "?") + "pgbouncer=true" } } });

const tables = await db.$queryRawUnsafe(`
  SELECT tablename FROM pg_tables
  WHERE schemaname='public' ORDER BY tablename
`);
console.log("tables:", tables.map((t) => t.tablename).join(", "));

for (const t of ["User", "user", "users", "Plan", "Booking", "Session", "Setting"]) {
  try {
    const r = await db.$queryRawUnsafe(
      `SELECT count(*)::int AS n FROM "${t}"`
    );
    console.log(`${t}: ${r[0].n} rows`);
  } catch {
    /* table absent */
  }
}

try {
  const recent = await db.$queryRawUnsafe(`
    SELECT email, "createdAt"::text AS created FROM "User" ORDER BY "createdAt" DESC LIMIT 5
  `);
  if (Array.isArray(recent) && recent.length) {
    console.log("latest users:");
    for (const u of recent) console.log("  ", u.email, u.created);
  }
} catch (e) {
  console.log("user query err:", e.message?.slice(0, 120));
}

await db.$disconnect();

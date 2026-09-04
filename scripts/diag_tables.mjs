import { PrismaClient } from "@prisma/client";

const TX_URL = "postgresql://postgres.REDACTED-C6-OLD-PROJ-REF:REDACTED-C6-DB-PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&pgbouncer=true&connection_limit=2";
const db = new PrismaClient({ datasources: { db: { url: TX_URL } } });

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

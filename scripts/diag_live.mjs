import { PrismaClient } from "@prisma/client";

// C-6 fix: credentials live only in env / the vault — never in this file.
const SESSION_URL = process.env.DATABASE_URL;
if (!SESSION_URL) {
  throw new Error("Set DATABASE_URL (session-pooler URL with ?schema=deyoung). Values live in workers/secrets/supabase.json.");
}
const TX_URL = SESSION_URL.replace(":5432", ":6543") + (SESSION_URL.includes("?") ? "&" : "?") + "pgbouncer=true";

const session = new PrismaClient({ datasources: { db: { url: SESSION_URL } } });
const tx = new PrismaClient({ datasources: { db: { url: TX_URL } } });

try {
  const rows = await session.$queryRawUnsafe(`
    SELECT coalesce(application_name,'') AS app, usename,
           CASE WHEN client_addr IS NULL THEN 'internal' ELSE host(client_addr) END AS client,
           state, count(*)::int AS n
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY 1,2,3,4 ORDER BY n DESC
  `);
  console.log("=== pg_stat_activity (via :5432 session pooler) ===");
  for (const r of rows) console.log(`${String(r.n).padStart(3)}  app=${r.app}  user=${r.usename}  client=${r.client}  state=${r.state}`);
} catch (e) {
  console.error("SESSION query FAILED:", e.message?.slice(0, 200));
}

try {
  const t0 = Date.now();
  const n = await tx.plan.count();
  console.log(`\n=== :6543 transaction pooler OK — plans=${n} (${Date.now() - t0}ms) ===`);
  const recent = await tx.$queryRawUnsafe(`
    SELECT count(*)::int AS users FROM "User"
  `).catch(() => [{ users: "n/a" }]);
  console.log("users table:", JSON.stringify(recent));
  const latest = await tx.$queryRawUnsafe(`
    SELECT email, "emailVerified" IS NOT NULL AS verified, "createdAt"::text
    FROM "User" ORDER BY "createdAt" DESC LIMIT 5
  `).catch(() => []);
  if (Array.isArray(latest) && latest.length) {
    console.log("latest users:");
    for (const u of latest) console.log(`  ${u.email}  verified=${u.verified}  ${u.createdAt}`);
  }
} catch (e) {
  console.error("TX pooler FAILED:", e.message?.slice(0, 200));
}

await session.$disconnect().catch(() => {});
await tx.$disconnect().catch(() => {});

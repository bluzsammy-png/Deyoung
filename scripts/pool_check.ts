/**
 * Inspect Supabase pooler usage + test transaction mode (6543).
 * Run: bun scripts/pool_check.ts
 */
import { PrismaClient } from "@prisma/client";

// C-6 fix: credentials live only in env / the vault — never in this file.
const SESSION = process.env.DATABASE_URL;
if (!SESSION) {
  throw new Error("Set DATABASE_URL (session-pooler URL with ?schema=deyoung). Values live in workers/secrets/supabase.json.");
}
const TXMODE = SESSION.replace(":5432", ":6543") + (SESSION.includes("?") ? "&" : "?") + "pgbouncer=true";

async function main() {
  // 1. Who is connected right now (via session pooler)?
  const s = new PrismaClient({ datasources: { db: { url: SESSION } } });
  const rows = await s.$queryRawUnsafe<any[]>(
    `SELECT coalesce(state,'-') AS state, coalesce(application_name,'-') AS app, count(*)::int AS n
     FROM pg_stat_activity WHERE datname='postgres' GROUP BY 1,2 ORDER BY 3 DESC`
  );
  console.log("== pg_stat_activity (session pooler view) ==");
  for (const r of rows) console.log(`${r.state} | ${r.app} | ${r.n}`);
  await s.$disconnect();

  // 2. Does transaction mode (6543) work for app-style queries?
  const t = new PrismaClient({ datasources: { db: { url: TXMODE } } });
  const plans = await t.plan.count();
  console.log("== 6543 transaction mode OK, plan rows:", plans);
  // concurrent burst like the healthcheck hammer
  const burst = await Promise.all(Array.from({ length: 12 }, () => t.settings.findFirst()));
  console.log("== 12 concurrent queries over 6543, results:", burst.filter(Boolean).length, "ok");
  await t.$disconnect();
}

main().catch((e) => { console.error("POOL_CHECK_FAIL:", e.message); process.exit(1); });

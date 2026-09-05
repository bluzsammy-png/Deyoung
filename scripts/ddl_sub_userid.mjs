// DDL: adds userId to "Subscription" in production Postgres (Supabase).
// Idempotent — safe to re-run.
//
//   1) npx prisma generate --schema prisma/schema.postgres.prisma
//   2) node scripts/ddl_sub_userid.mjs
//   3) npx prisma generate   (restore sqlite client for local dev)
import { PrismaClient } from "@prisma/client";

const TX_URL = "postgresql://postgres.jqicshfafusomwqifsrw:fAdrS5t3R%23cYNRY@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&pgbouncer=true&connection_limit=2";
const db = new PrismaClient({ datasources: { db: { url: TX_URL } } });

console.log("— adding Subscription.userId …");
await db.$executeRawUnsafe(`
  ALTER TABLE "Subscription" ADD COLUMN IF NOT EXISTS "userId" TEXT NOT NULL DEFAULT ''
`);
console.log("  ok");

console.log("— index for account lookups …");
await db.$executeRawUnsafe(`CREATE INDEX IF NOT EXISTS "Subscription_userId_idx" ON "Subscription"("userId")`);
console.log("  ok");

console.log("— backfill: stamp userId on active subs whose email matches a User …");
const rows = await db.$queryRawUnsafe(
  `UPDATE "Subscription" s SET "userId" = u.id
   FROM "User" u
   WHERE s."userId" = '' AND lower(u.email) = lower(s.email)`
);
console.log("  backfilled", rows, "rows");

console.log("— verify …");
const check = await db.$queryRawUnsafe(
  `SELECT column_name, data_type, column_default FROM information_schema.columns
   WHERE table_name = 'Subscription' AND column_name = 'userId'`
);
console.log(check);

await db.$disconnect();
console.log("DDL_DONE");

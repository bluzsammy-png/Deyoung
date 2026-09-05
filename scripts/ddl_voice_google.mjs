// DDL: adds googleId to "User" + creates "VoiceClone" table in production
// Postgres (Supabase). Idempotent — safe to re-run.
//
//   1) npx prisma generate --schema prisma/schema.postgres.prisma
//   2) node scripts/ddl_voice_google.mjs
//   3) npx prisma generate   (restore sqlite client for local dev)
import { PrismaClient } from "@prisma/client";

const TX_URL = "postgresql://postgres.jqicshfafusomwqifsrw:fAdrS5t3R%23cYNRY@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&pgbouncer=true&connection_limit=2";
const db = new PrismaClient({ datasources: { db: { url: TX_URL } } });

console.log("— adding User.googleId …");
await db.$executeRawUnsafe(`
  ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "googleId" TEXT NOT NULL DEFAULT ''
`);
console.log("  ok");

console.log("— creating VoiceClone table …");
await db.$executeRawUnsafe(`
  CREATE TABLE IF NOT EXISTS "VoiceClone" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "userEmail" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "ownerType" TEXT NOT NULL DEFAULT 'self',
    "sampleUrl" TEXT NOT NULL,
    "consentUrl" TEXT NOT NULL,
    "writtenConsentUrl" TEXT NOT NULL DEFAULT '',
    "consentPhrase" TEXT NOT NULL DEFAULT '',
    "licenseVersion" TEXT NOT NULL DEFAULT 'v1',
    "status" TEXT NOT NULL DEFAULT 'licensed',
    "reviewStatus" TEXT NOT NULL DEFAULT 'pending',
    "reviewNotes" TEXT NOT NULL DEFAULT '',
    "revokedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "VoiceClone_pkey" PRIMARY KEY ("id")
  )
`);
await db.$executeRawUnsafe(`CREATE INDEX IF NOT EXISTS "VoiceClone_userId_idx" ON "VoiceClone"("userId")`);
await db.$executeRawUnsafe(`CREATE INDEX IF NOT EXISTS "VoiceClone_status_idx" ON "VoiceClone"("status")`);
console.log("  ok");

const cols = await db.$queryRawUnsafe(`
  SELECT column_name FROM information_schema.columns
  WHERE table_name='User' AND column_name='googleId'
`);
const tables = await db.$queryRawUnsafe(`
  SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='VoiceClone'
`);
console.log(`verify: User.googleId=${cols.length} VoiceClone table=${tables.length}`);
await db.$disconnect();
console.log("done");

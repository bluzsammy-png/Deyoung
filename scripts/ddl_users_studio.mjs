// One-off: additive DDL for User accounts + studio fields on LIVE Supabase.
// Mirrors prisma db push but avoids the flaky migration engine on the tx pooler.
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const DDL = [
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "userId" TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "model" TEXT NOT NULL DEFAULT 'deyo.1'`,
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "stage" TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "progress" INTEGER NOT NULL DEFAULT 0`,
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "voice" TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE "VideoRequest" ADD COLUMN IF NOT EXISTS "refImageUrl" TEXT NOT NULL DEFAULT ''`,
  `CREATE TABLE IF NOT EXISTS "User" (
      "id" TEXT NOT NULL,
      "email" TEXT NOT NULL,
      "passwordHash" TEXT NOT NULL,
      "name" TEXT NOT NULL DEFAULT '',
      "phone" TEXT NOT NULL DEFAULT '',
      "avatarUrl" TEXT NOT NULL DEFAULT '',
      "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
      "updatedAt" TIMESTAMP(3) NOT NULL,
      CONSTRAINT "User_pkey" PRIMARY KEY ("id")
   )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "User_email_key" ON "User"("email")`,
  `CREATE TABLE IF NOT EXISTS "SupportMessage" (
      "id" TEXT NOT NULL,
      "userId" TEXT NOT NULL,
      "userEmail" TEXT NOT NULL,
      "fromUser" BOOLEAN NOT NULL DEFAULT true,
      "body" TEXT NOT NULL,
      "read" BOOLEAN NOT NULL DEFAULT false,
      "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT "SupportMessage_pkey" PRIMARY KEY ("id")
   )`,
  `CREATE INDEX IF NOT EXISTS "SupportMessage_userId_idx" ON "SupportMessage"("userId")`,
];

async function main() {
  for (const sql of DDL) {
    await prisma.$executeRawUnsafe(sql);
    console.log('OK:', sql.slice(0, 60).replace(/\s+/g, ' '));
  }
  const users = await prisma.$queryRawUnsafe(`SELECT count(*)::int AS n FROM "User"`);
  const vr = await prisma.$queryRawUnsafe(`SELECT count(*)::int AS n FROM "VideoRequest" WHERE "model"='deyo.1'`);
  console.log('verify: User rows =', users[0].n, '| VideoRequest.model default rows =', vr[0].n);
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());

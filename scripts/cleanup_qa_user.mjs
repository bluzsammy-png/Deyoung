// One-off: remove QA studio test rows from LIVE Supabase.
import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
const email = "qa-studio-0905@deyoung.site";
const u = await prisma.user.findUnique({ where: { email } });
if (u) {
  await prisma.supportMessage.deleteMany({ where: { userId: u.id } });
  await prisma.user.delete({ where: { id: u.id } });
  console.log("removed QA user + messages");
} else console.log("QA user not found");
await prisma.$disconnect();

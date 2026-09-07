/* Dev QA helper — inspect User rows (read-only). */
const { PrismaClient } = require("@prisma/client");
const p = new PrismaClient();
(async () => {
  const users = await p.user.findMany({
    select: { email: true, role: true, status: true, provider: true, createdAt: true },
  });
  console.log(JSON.stringify(users, null, 1));
  const subs = await p.subscription.findMany({
    where: { planCode: "admin-free" },
    select: { id: true, email: true, status: true },
  });
  console.log("admin-free subs:", JSON.stringify(subs));
  const queue = await p.videoRequest.findMany({
    where: { status: { in: ["queued", "rendering"] } },
    select: { id: true, status: true, email: true, createdAt: true },
    orderBy: { createdAt: "desc" },
    take: 5,
  });
  console.log("active renders:", JSON.stringify(queue));
  await p.$disconnect();
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});

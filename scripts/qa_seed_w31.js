/* Task 62-d W3.1 dev QA seed — LOCAL sqlite only (db/custom.db).
 * Seeds: 1 admin + 3 VideoRequest rows (rendering w/ H3-style progress note,
 * queued w/ empty notes, done w/ delivery note) to exercise the new
 * worker-identity line in the admin Video Queue. Deleted again by --cleanup. */
const crypto = require("crypto");
const { PrismaClient } = require("@prisma/client");

const hashPassword = (pw) => {
  const salt = crypto.randomBytes(16).toString("hex");
  return `scrypt$${salt}$${crypto.scryptSync(pw, salt, 64).toString("hex")}`;
};

const db = new PrismaClient();
const mode = process.argv[2] || "seed";

(async () => {
  if (mode === "cleanup") {
    await db.videoRequest.deleteMany({ where: { email: "qa-w31@deyoung.local" } });
    await db.admin.deleteMany({ where: { email: "admin@deyoung.site" } });
    console.log("cleanup done — stock empty sqlite restored");
    await db.$disconnect();
    return;
  }
  const pw = "qa-w31-temp-" + crypto.randomBytes(6).toString("hex");
  await db.admin.upsert({
    where: { email: "admin@deyoung.site" },
    update: { passwordHash: hashPassword(pw) },
    create: { email: "admin@deyoung.site", passwordHash: hashPassword(pw) },
  });
  await db.videoRequest.create({
    data: {
      subscriptionId: "qa-w31-sub", email: "qa-w31@deyoung.local",
      prompt: "QA W3.1: verify the worker identity line renders in the Video Queue",
      seconds: 10, resolution: "1080p", status: "rendering",
      notes: "claimed by lightning-h3-qatest at 2026-09-10T12:00:00Z — H3 sampling running — 145 frames @ 960x544, steps=4, 3.2 min elapsed",
    },
  });
  await db.videoRequest.create({
    data: {
      subscriptionId: "qa-w31-sub", email: "qa-w31@deyoung.local",
      prompt: "QA W3.1: queued row with NO notes — identity line must stay hidden",
      seconds: 5, resolution: "720p", status: "queued", notes: "",
    },
  });
  await db.videoRequest.create({
    data: {
      subscriptionId: "qa-w31-sub", email: "qa-w31@deyoung.local",
      prompt: "QA W3.1: done row — claim + delivery notes both meaningful",
      seconds: 8, resolution: "1080p", status: "done", notes: "rendered by lightning-h3-qatest/h3(len193,s4) — delivered 2026-09-10T12:20:00Z",
      resultUrl: "/api/files/qa-none",
    },
  });
  console.log("SEEDED. temp admin pw:", pw);
  await db.$disconnect();
})();

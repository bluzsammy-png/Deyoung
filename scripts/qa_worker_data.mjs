// QA harness for the worker plane: seed test data / verify / cleanup.
// usage: node scripts/qa_worker_data.mjs seed|verify|cleanup <email> <requestId?>
import { PrismaClient } from "@prisma/client";
import { readFileSync } from "node:fs";

const url = readFileSync(".env", "utf8").match(/DATABASE_URL="?([^"\n]+)"?/)?.[1];
process.env.DATABASE_URL = url;
const db = new PrismaClient();
const [cmd, email, reqId] = process.argv.slice(2);

if (cmd === "seed") {
  const sub = await db.subscription.create({
    data: {
      name: "Worker QA", email, planCode: "pro", status: "active", provider: "manual",
      periodStart: new Date(), periodEnd: new Date(Date.now() + 30 * 864e5),
    },
  });
  const jobs = [];
  for (const prompt of [
    "A neon koi fish swimming through a rainy Lagos skyline at night, cinematic",
    "Golden retriever puppies chasing a red balloon across a sunny field, slow motion",
  ]) {
    jobs.push(await db.videoRequest.create({
      data: { subscriptionId: sub.id, email, prompt, seconds: 5, resolution: "720p", withAudio: false, watermark: true, queuePriority: 10, status: "queued" },
    }));
  }
  console.log(JSON.stringify({ subscriptionId: sub.id, jobIds: jobs.map(j => j.id) }));
} else if (cmd === "verify") {
  const req = await db.videoRequest.findUnique({ where: { id: reqId } });
  console.log(JSON.stringify({ status: req?.status, resultUrl: req?.resultUrl, gpuMinutes: req?.gpuMinutes, notes: req?.notes }));
} else if (cmd === "cleanup") {
  const req = await db.videoRequest.findUnique({ where: { id: reqId } });
  if (req) await db.videoRequest.delete({ where: { id: reqId } });
  const subs = await db.subscription.findMany({ where: { email } });
  for (const s of subs) await db.subscription.delete({ where: { id: s.id } });
  console.log("cleaned");
}
await db.$disconnect();

/* QA setup — fresh end-user funnel for browser QA (shared DB: QA-marked rows only).
 * 1) signup qa-stream@deyoungqa.local via the real API
 * 2) attach a beginner subscription (notes QA) so renders are allowed
 * 3) queue one render via the real public /api/requests API
 */
const BASE = "http://localhost:3000";
const EMAIL = "qa-stream@deyoungqa.local";
const PASSWORD = "qa-stream-pass-123";

(async () => {
  const su = await fetch(`${BASE}/api/auth/signup`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "QA Stream", email: EMAIL, password: PASSWORD }),
  });
  console.log("signup:", su.status, (await su.text()).slice(0, 120));

  const { PrismaClient } = require("@prisma/client");
  const p = new PrismaClient();
  const plan = await p.plan.findUnique({ where: { code: "beginner" } });
  if (!plan) throw new Error("beginner plan missing — run seed");
  const sub = await p.subscription.upsert({
    where: { id: "qa-stream-sub" },
    update: { status: "active" },
    create: {
      id: "qa-stream-sub",
      name: "QA Stream",
      email: EMAIL,
      planCode: "beginner",
      status: "active",
      provider: "manual",
      notes: "QA browser-test subscription — safe to delete",
    },
  });
  console.log("sub:", sub.id, sub.status);

  const r = await fetch(`${BASE}/api/requests`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: EMAIL,
      prompt: "Browser QA — a paper boat races down a rain gutter, cinematic macro shots",
      seconds: 5, resolution: "720p", withAudio: false,
    }),
  });
  const body = await r.json();
  console.log("render:", r.status, JSON.stringify(body).slice(0, 160));
  await p.$disconnect();
})().catch((e) => { console.error(e.message); process.exit(1); });

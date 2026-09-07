/* QA E2E — live film simulator (SSE) + render mail hooks, against the dev server.
 * Read-only on credentials; mutates only QA-owned rows. Run: node scripts/qa_stream_e2e.js
 */
const crypto = require("crypto");
const fs = require("fs");
const { PrismaClient } = require("@prisma/client");
const p = new PrismaClient();

const BASE = "http://localhost:3000";
const env = Object.fromEntries(
  fs.readFileSync(".env.local", "utf8").split("\n").filter((l) => l.includes("=") && !l.startsWith("#")).map((l) => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim()])
);
const AUTH_SECRET = env.AUTH_SECRET;
const WORKER_TOKEN = env.WORKER_TOKEN;
if (!AUTH_SECRET || !WORKER_TOKEN) { console.error("missing env"); process.exit(1); }

const b64url = (s) => Buffer.from(s).toString("base64url");
const sign = (payload) => {
  const body = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac("sha256", AUTH_SECRET).update(body).digest("base64url");
  return `${body}.${sig}`;
};
const results = [];
const check = (name, cond, extra = "") => { results.push([cond ? "PASS" : "FAIL", name, extra]); };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Capture SSE frames for `ms` milliseconds. */
function captureSSE(requestId, cookie, ms) {
  return new Promise((resolve) => {
    const http = require("http");
    const req = http.get(
      `${BASE}/api/studio/stream?requestId=${encodeURIComponent(requestId)}`,
      { headers: { Cookie: cookie, Accept: "text/event-stream" } },
      (res) => {
        let raw = "";
        res.on("data", (d) => (raw += d.toString()));
        const timer = setTimeout(() => { res.destroy(); finish(); }, ms);
        const finish = () => {
          clearTimeout(timer);
          const frames = raw.split("\n\n").filter((f) => f.startsWith("event:"));
          resolve({ status: res.statusCode, frames });
        };
        res.on("end", finish);
        res.on("error", finish);
      }
    );
    req.on("error", () => resolve({ status: 0, frames: [] }));
  });
}

(async () => {
  // ---- setup: mint cookies straight from the app's own token format ----
  const owner = await p.user.findUnique({ where: { email: "deyoungsltd@gmail.com" } });
  const qa = await p.user.findUnique({ where: { email: "qa-user@test.local" } });
  if (!owner || !qa) { console.error("seed users missing"); process.exit(1); }
  const exp = Math.floor(Date.now() / 1000) + 1800;
  const ownerCookie = `dy_user=${sign({ sub: owner.id, email: owner.email, exp, role: "user" })}`;
  const qaCookie = `dy_user=${sign({ sub: qa.id, email: qa.email, exp, role: "user" })}`;

  // ---- hygiene: retire ONLY known QA rows (by id / QA prompt prefix — the DB is shared with prod) ----
  const stale = await p.videoRequest.updateMany({
    where: { status: "queued", id: { in: ["cmtqlbqrg0008jx1zmpj774sg", "cmtqlc0pv000ajx1z9ahd3n51", "cmtqlfqw4000djx1zdkw0y8yj"] } },
    data: { status: "cancelled", notes: "retired by QA — stale W2 test row" },
  });
  const stale2 = await p.videoRequest.updateMany({
    where: { status: { in: ["queued", "rendering"] }, prompt: { startsWith: "QA stream E2E" } },
    data: { status: "cancelled", notes: "retired by QA — previous QA run artifact" },
  });
  console.log("stale rows cancelled:", stale.count + stale2.count);

  // ---- guard 1: no cookie -> 401 ----
  const anon = await captureSSE("cmtqlfqw4000djx1zdkw0y8yj", "dy_user=none", 2500);
  check("SSE rejects anonymous (401)", anon.status === 401, `got ${anon.status}`);

  // ---- guard 2: non-owner, non-admin -> 403 ----
  const intruder = await captureSSE("cmtqlfqw4000djx1zdkw0y8yj", qaCookie, 2500);
  check("SSE rejects foreign user (403)", intruder.status === 403, `got ${intruder.status}`);

  // ---- submit a real studio render as the owner ----
  const submit = await fetch(`${BASE}/api/studio/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: ownerCookie },
    body: JSON.stringify({
      prompt: "QA stream E2E — golden-hour drone pullback over a neon harbor, watercolor haze",
      seconds: 10, resolution: "1080p", withAudio: true, projectId: "", sceneId: "",
    }),
  });
  const submitBody = await submit.json();
  check("studio render accepted (201)", submit.status === 201, JSON.stringify(submitBody).slice(0, 120));
  const rid = submitBody?.request?.id;
  if (!rid) { console.error("no requestId — aborting"); await p.$disconnect(); process.exit(1); }

  // ---- phase 1: agent planning + queue (first ~6s of life) ----
  const phase1 = await captureSSE(rid, ownerCookie, 6000);
  const t1 = phase1.frames.filter((f) => f.startsWith("event: trace")).map((f) => JSON.parse(f.split("data: ")[1]));
  const last1 = t1[t1.length - 1];
  check("SSE 200 + trace frames flowing", phase1.status === 200 && t1.length > 2, `${t1.length} frames`);
  check("agent steps done (brief/parse/cast/storyboard)", ["brief", "parse", "cast", "storyboard"].every((id) => last1?.steps.find((s) => s.id === id)?.state === "done"));
  check("queue step active with position", last1?.steps.find((s) => s.id === "queue")?.state === "active" && /position #\d+/.test(last1?.steps.find((s) => s.id === "queue")?.detail || ""), last1?.steps.find((s) => s.id === "queue")?.detail);

  // ---- worker claims exactly our job ----
  const claim = await fetch(`${BASE}/api/worker/claim`, {
    method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${WORKER_TOKEN}` },
    body: JSON.stringify({ agent: "qa-stream-worker" }),
  });
  const claimBody = await claim.json();
  check("worker claims our job", claimBody?.job?.id === rid, `claimed ${claimBody?.job?.id}`);

  // ---- phase 2: GPU rendering phase trace ----
  const phase2 = await captureSSE(rid, ownerCookie, 5000);
  const t2 = phase2.frames.filter((f) => f.startsWith("event: trace")).map((f) => JSON.parse(f.split("data: ")[1]));
  const last2 = t2[t2.length - 1];
  check("trace flips to GPU phase", last2?.phase === "gpu" && /rendering/i.test(last2?.headline || ""), last2?.headline);
  const active2 = last2?.steps.find((s) => s.state === "active");
  check("a GPU pass step is active", Boolean(active2), active2?.label);

  // ---- deliver: real multipart to object storage (minimal mp4) ----
  const mp4 = Buffer.concat([Buffer.from([0, 0, 0, 0x18]), Buffer.from("ftypmp42"), Buffer.alloc(24, 0x42)]);
  const form = new FormData();
  form.append("action", "deliver");
  form.append("gpuMinutes", "0.2");
  form.append("renderer", "qa-stream-worker");
  form.append("file", new Blob([mp4], { type: "video/mp4" }), "qa.mp4");
  const deliver = await fetch(`${BASE}/api/worker/jobs/${rid}`, {
    method: "PATCH", headers: { Authorization: `Bearer ${WORKER_TOKEN}` }, body: form,
  });
  const deliverBody = await deliver.json();
  check("multipart delivery accepted", deliver.status === 200 && deliverBody?.request?.status === "done", JSON.stringify(deliverBody).slice(0, 140));

  // ---- phase 3: terminal — one trace (done) then end, connection closes ----
  const phase3 = await captureSSE(rid, ownerCookie, 6000);
  const t3 = phase3.frames.filter((f) => f.startsWith("event: trace")).map((f) => JSON.parse(f.split("data: ")[1]));
  const end3 = phase3.frames.find((f) => f.startsWith("event: end"));
  const last3 = t3[t3.length - 1];
  check("terminal trace shows done + resultUrl", last3?.status === "done" && Boolean(last3?.resultUrl), last3?.resultUrl);
  check("delivery steps done (encode/deliver)", ["encode", "deliver"].every((id) => last3?.steps.find((s) => s.id === id)?.state === "done"));
  check("stream sends end event and closes", Boolean(end3), end3?.split("data: ")[1]);

  // ---- failure path: mail hook + honest failed state ----
  const submit2 = await fetch(`${BASE}/api/studio/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: ownerCookie },
    body: JSON.stringify({ prompt: "QA stream E2E — failure branch", seconds: 5, resolution: "720p", withAudio: false }),
  });
  const rid2 = (await submit2.json())?.request?.id;
  const fail = await fetch(`${BASE}/api/worker/jobs/${rid2}`, {
    method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${WORKER_TOKEN}` },
    body: JSON.stringify({ action: "fail", agent: "qa-stream-worker", notes: "QA: simulated poison prompt" }),
  });
  const failBody = await fail.json();
  check("fail action honest-fails the job", fail.status === 200 && failBody?.request?.status === "failed", JSON.stringify(failBody));

  console.log("\n===== RESULTS =====");
  for (const [st, name, extra] of results) console.log(`${st}  ${name}${extra ? `  —  ${extra}` : ""}`);
  const failed = results.filter((r) => r[0] === "FAIL").length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  await p.$disconnect();
  process.exit(failed ? 1 : 0);
})().catch(async (e) => { console.error(e); await p.$disconnect(); process.exit(1); });

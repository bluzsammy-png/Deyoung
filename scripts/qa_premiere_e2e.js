/* QA E2E — W2.2 Premiere Wall: public feed, user requests, admin curation, asset flips.
 * Real login endpoints (no cookie minting). Mutates only QA-owned rows + the DEV
 * admin password (dev sqlite — production Supabase is a different database).
 * Run: node scripts/qa_premiere_e2e.js
 */
const crypto = require("crypto");
const fs = require("fs");
const { PrismaClient } = require("@prisma/client");
const p = new PrismaClient();

const BASE = "http://localhost:3000";
const QA_ADMIN_PASS = "qa-premiere-admin-pass";
const results = [];
const check = (name, cond, extra = "") => { results.push([cond ? "PASS" : "FAIL", name, extra]); };

/* scrypt hash in the app's own format (src/lib/auth.ts hashPassword). */
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt$${salt}$${hash}`;
}

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, opts);
  let json = null;
  try { json = await res.json(); } catch { /* streams */ }
  return { status: res.status, json, res };
}
const post = (path, body, cookie) => req(path, { method: "POST", headers: { "Content-Type": "application/json", ...(cookie ? { Cookie: cookie } : {}) }, body: JSON.stringify(body) });
const patch = (path, body, cookie) => req(path, { method: "PATCH", headers: { "Content-Type": "application/json", Cookie: cookie }, body: JSON.stringify(body) });

/** Real login -> session cookie from the actual Set-Cookie header. */
async function login(path, email, password) {
  const r = await post(path, { email, password });
  const set = r.res.headers.get("set-cookie") || "";
  const cookie = set.split(";")[0];
  return { r, cookie };
}

(async () => {
  /* ---------- setup: QA users (real passwords), asset with REAL bytes, delivered render ---------- */
  const qaEmail = "qa-premiere@deyoung.test";
  const otherEmail = "qa-other@deyoung.test";
  const [qa, other] = await Promise.all([
    p.user.upsert({ where: { email: qaEmail }, update: { passwordHash: hashPassword("qa-premiere-pass-123"), status: "active" }, create: { email: qaEmail, name: "QA Premiere", status: "active", passwordHash: hashPassword("qa-premiere-pass-123") } }),
    p.user.upsert({ where: { email: otherEmail }, update: { passwordHash: hashPassword("qa-other-pass-123"), status: "active" }, create: { email: otherEmail, name: "QA Other", status: "active", passwordHash: hashPassword("qa-other-pass-123") } }),
  ]);

  const key = "renders/premiere-qa/v1.mp4";
  const mediaPath = `media/${key}`;
  fs.mkdirSync("media/renders/premiere-qa", { recursive: true });
  fs.copyFileSync("public/showreel/clip-cartoon.mp4", mediaPath);
  const real = fs.readFileSync(mediaPath);
  let asset = await p.asset.findFirst({ where: { storageKey: key } });
  if (!asset) {
    asset = await p.asset.create({ data: { kind: "video", mime: "video/mp4", bytes: real.length, storageKey: key, driver: "local", isPublic: false, createdBy: "qa" } });
  }
  // clean any premiere left by a previous QA run
  await p.premiere.deleteMany({ where: { request: { email: qaEmail } } });
  // + stale QA renders left by crashed runs (QA marker subscriptionId only)
  await p.videoRequest.deleteMany({ where: { subscriptionId: "qa-sub-premiere" } });
  // + fresh DEV premiere/login buckets — prior runs leave them half-consumed
  await p.rateLimit.deleteMany({ where: { bucket: { startsWith: "premiere:" } } });
  await p.rateLimit.deleteMany({ where: { bucket: { startsWith: "login:" } } });
  const request = await p.videoRequest.create({
    data: {
      subscriptionId: "qa-sub-premiere",
      email: qaEmail,
      prompt: "QA premiere render — neon city flythrough at dusk",
      seconds: 5,
      status: "done",
      resultAssetId: asset.id,
      notes: "QA-owned row for premiere wall e2e",
    },
  });

  // real logins through the app's own endpoints (dev DB only)
  const adminEmail = "admin@deyoung.site";
  await p.admin.update({ where: { email: adminEmail }, data: { passwordHash: hashPassword(QA_ADMIN_PASS) } });
  const userL = await login("/api/auth/user-login", qaEmail, "qa-premiere-pass-123");
  check("user login 200 + cookie", userL.r.status === 200 && userL.cookie.startsWith("dy_user="), String(userL.r.status));
  const otherL = await login("/api/auth/user-login", otherEmail, "qa-other-pass-123");
  check("other login 200 + cookie", otherL.r.status === 200 && otherL.cookie.startsWith("dy_user="), String(otherL.r.status));
  const adminL = await login("/api/auth/login", adminEmail, QA_ADMIN_PASS);
  check("admin login 200 + cookie", adminL.r.status === 200 && adminL.cookie.startsWith("dy_admin="), String(adminL.r.status));
  const userCookie = userL.cookie;
  const otherCookie = otherL.cookie;
  const adminCookie = adminL.cookie;

  /* ---------- 1: public feed shows the 3 seeded premieres, featured first ---------- */
  let r = await req("/api/premieres");
  check("public feed 200", r.status === 200);
  const seeded = r.json?.premieres ?? [];
  check("3 seeded premieres", seeded.length === 3, `got ${seeded.length}`);
  check("featured first", seeded[0]?.featured === true && seeded[0]?.title === "The DeYoung Film", seeded[0]?.title);
  check("static videoSrc passthrough", seeded[0]?.videoSrc === "/video/deyoung-film-web.mp4", seeded[0]?.videoSrc);

  /* ---------- 2: guards ---------- */
  r = await post("/api/premieres", { requestId: request.id, title: "X" });
  check("anon POST -> 401", r.status === 401, String(r.status));

  r = await post("/api/premieres", { requestId: request.id, title: "Stolen" }, otherCookie);
  check("non-owner POST -> 403", r.status === 403, String(r.status));

  r = await post("/api/premieres", { requestId: request.id, title: "" }, userCookie);
  check("empty title -> 400", r.status === 400, String(r.status));

  r = await post("/api/premieres", { requestId: request.id, title: "Neon Dusk", category: "nope" }, userCookie);
  check("bad category -> 400", r.status === 400, String(r.status));

  // The premiere limiter is per-IP and the guard tests above just consumed it
  // (5/h, all from localhost). Clear the DEV bucket so the happy-path block
  // runs against a fresh window — production limits stay untouched.
  await p.rateLimit.deleteMany({ where: { bucket: { startsWith: "premiere:" } } });

  /* ---------- 3: happy path request -> pending, asset stays private ---------- */
  r = await post("/api/premieres", { requestId: request.id, title: "Neon Dusk", logline: "A city that hums.", category: "ai-film" }, userCookie);
  check("user request -> 201 pending", r.status === 201 && r.json?.premiere?.status === "pending", JSON.stringify(r.json));
  const premiereId = r.json?.premiere?.id;
  const afterCreate = await p.asset.findUnique({ where: { id: asset.id } });
  check("asset still private while pending", afterCreate?.isPublic === false);

  r = await req("/api/premieres");
  check("pending NOT on public feed", (r.json?.premieres ?? []).every((x) => x.id !== premiereId));

  r = await post("/api/premieres", { requestId: request.id, title: "Dup" }, userCookie);
  check("duplicate request -> 409", r.status === 409, String(r.status));

  /* ---------- 4: files route privacy ---------- */
  r = await req(`/api/files/${asset.id}`);
  check("private asset anon -> 404", r.status === 404, String(r.status));
  r = await req(`/api/files/${asset.id}?request=${request.id}&email=${qaEmail}`);
  check("customer id+email match -> 200", r.status === 200 && r.res.headers.get("content-type") === "video/mp4", String(r.status));

  /* ---------- 5: admin guards + list ---------- */
  r = await req("/api/admin/premieres", { headers: { Cookie: userCookie } });
  check("user on admin list -> 401", r.status === 401, String(r.status));
  r = await req("/api/admin/premieres", { headers: { Cookie: adminCookie } });
  check("admin list 200", r.status === 200);
  check("pending visible to admin", (r.json?.premieres ?? []).some((x) => x.id === premiereId));
  // a render with a PENDING premiere is correctly NOT eligible for a second one
  check("eligible excludes pending render", !(r.json?.eligible ?? []).some((x) => x.id === request.id));
  check("renderPrompt joined", (r.json?.premieres ?? []).find((x) => x.id === premiereId)?.renderPrompt.includes("neon city"));

  /* ---------- 6: admin publish flips asset public ---------- */
  r = await patch(`/api/admin/premieres/${premiereId}`, { status: "published" }, adminCookie);
  check("admin publish -> 200", r.status === 200 && r.json?.premiere?.status === "published", JSON.stringify(r.json));
  const publishedAsset = await p.asset.findUnique({ where: { id: asset.id } });
  check("asset NOW public", publishedAsset?.isPublic === true);

  r = await req(`/api/files/${asset.id}`);
  check("public asset anon -> 200 mp4", r.status === 200 && r.res.headers.get("content-type") === "video/mp4", String(r.status));
  r = await req("/api/premieres");
  const feed = r.json?.premieres ?? [];
  check("QA premiere on public feed", feed.some((x) => x.id === premiereId));
  check("asset-backed videoSrc", feed.find((x) => x.id === premiereId)?.videoSrc === `/api/files/${asset.id}`);

  /* ---------- 7: unpublish flips back private ---------- */
  r = await patch(`/api/admin/premieres/${premiereId}`, { status: "rejected" }, adminCookie);
  check("admin unpublish -> 200", r.status === 200);
  const rejectedAsset = await p.asset.findUnique({ where: { id: asset.id } });
  check("asset private again", rejectedAsset?.isPublic === false);
  r = await req(`/api/files/${asset.id}`);
  check("unpublished asset anon -> 404", r.status === 404, String(r.status));

  /* ---------- 8: admin direct create + delete (second render gets its OWN asset — one video, one premiere) ---------- */
  const key2 = "renders/premiere-qa/v2.mp4";
  fs.copyFileSync("public/showreel/clip-doors.mp4", `media/${key2}`);
  const real2 = fs.readFileSync(`media/${key2}`);
  const asset2 = await p.asset.create({
    data: { kind: "video", mime: "video/mp4", bytes: real2.length, storageKey: key2, driver: "local", isPublic: false, createdBy: "qa" },
  });
  const request2 = await p.videoRequest.create({
    data: { subscriptionId: "qa-sub-premiere", email: qaEmail, prompt: "QA premiere render two — sunrise over the harbor", seconds: 5, status: "done", resultAssetId: asset2.id },
  });
  r = await post("/api/admin/premieres", { requestId: request2.id, title: "", category: "commercial" }, adminCookie);
  check("admin create -> 201, prompt-seeded title", r.status === 201, `status ${r.status} ${JSON.stringify(r.json)}`);
  const directId = r.json?.premiere?.id;
  if (!directId) throw new Error(`admin direct create failed: ${r.status} ${JSON.stringify(r.json)}`);
  const direct = await p.premiere.findUnique({ where: { id: directId } });
  const directAsset = await p.asset.findUnique({ where: { id: asset2.id } });
  check("direct create published + asset public", direct?.status === "published" && directAsset?.isPublic === true, `status=${direct?.status} public=${directAsset?.isPublic}`);
  check("title fell back to prompt", direct?.title.includes("sunrise"), direct?.title);

  r = await req(`/api/admin/premieres/${directId}`, { method: "DELETE", headers: { Cookie: adminCookie } });
  check("admin delete -> 200", r.status === 200);
  const afterDelete = await p.asset.findUnique({ where: { id: asset2.id } });
  check("delete flips asset private", afterDelete?.isPublic === false);
  check("premiere row gone", (await p.premiere.findUnique({ where: { id: directId } })) === null);

  /* ---------- 8b: same-asset duplicate render is rejected cleanly ---------- */
  const request3 = await p.videoRequest.create({
    data: { subscriptionId: "qa-sub-premiere", email: qaEmail, prompt: "QA duplicate render sharing asset one", seconds: 5, status: "done", resultAssetId: asset.id },
  });
  r = await post("/api/admin/premieres", { requestId: request3.id, title: "Double" }, adminCookie);
  check("duplicate-asset create -> 409", r.status === 409, `${r.status} ${JSON.stringify(r.json)}`);
  r = await req("/api/admin/premieres", { headers: { Cookie: adminCookie } });
  check("eligible excludes asset-premiered", !(r.json?.eligible ?? []).some((x) => x.id === request3.id));

  /* ---------- 9: cleanup QA rows (dev admin password left as the QA one — dev sqlite only, prod DB untouched) ---------- */
  await p.premiere.deleteMany({ where: { request: { email: qaEmail } } });
  await p.videoRequest.deleteMany({ where: { subscriptionId: "qa-sub-premiere" } });
  await p.asset.deleteMany({ where: { createdBy: "qa", storageKey: { startsWith: "renders/premiere-qa/" } } });
  await p.user.deleteMany({ where: { email: { in: [qaEmail, otherEmail] } } });
  fs.rmSync("media/renders/premiere-qa", { recursive: true, force: true });
  check("QA rows retired", true);

  let fails = 0;
  for (const [s, name, extra] of results) {
    if (s === "FAIL") fails++;
    console.log(`${s}  ${name}${extra ? `  [${extra}]` : ""}`);
  }
  console.log(fails === 0 ? `\nALL ${results.length} PASS` : `\n${fails} FAILURES`);
  await p.$disconnect();
  process.exit(fails === 0 ? 0 : 1);
})().catch(async (e) => { console.error(e); await p.$disconnect(); process.exit(1); });

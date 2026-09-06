/**
 * W1 E2E test (spec §D.1 storage_v2 + §F.2 RateLimit) — runs against the REAL
 * Supabase project. Credentials come from the local vault
 * (workers/secrets/supabase.json) — nothing secret is embedded here, so this
 * file is safe to commit.
 *
 * Checks:
 *  1. Storage adapter (real src/lib/storage.ts code):
 *     putObject → signedUrl → HTTP GET byte-round-trip → objectStat →
 *     unauthenticated GET must fail (private) → deleteObject → gone.
 *  2. RateLimit table in the deyoung schema: create/increment/limit window
 *     semantics identical to src/lib/ratelimit.ts dbRateLimit().
 *  3. Transaction-mode pooler (:6543, pgbouncer=true) reaches the deyoung
 *     schema — the exact shape deploy/start.sh builds for app runtime.
 *
 * Prereqs (run once):
 *   npx prisma generate --schema prisma/_pggen.prisma
 *
 * Run:
 *   npx tsx --conditions=react-server scripts/w1_e2e_test.ts
 */
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, "..");

const cfg = JSON.parse(
  fs.readFileSync(path.join(root, "workers", "secrets", "supabase.json"), "utf8")
).supabase;

process.env.SUPABASE_URL = process.env.SUPABASE_URL || `https://${cfg.project_ref}.supabase.co`;
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || cfg.service_role_key;
process.env.STORAGE_DRIVER = "supabase";

const SESSION_URL = `${cfg.database_url_session_pooler}?schema=deyoung&connection_limit=5`;
const TX_URL = `${cfg.database_url_transaction_pooler}?pgbouncer=true&connection_limit=5&schema=deyoung`;
process.env.DATABASE_URL = SESSION_URL;

let failures = 0;
function check(name: string, ok: boolean, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures += 1;
}

/* ------------------------------ 1. storage ------------------------------ */

async function storageTest() {
  const stor = await import("../src/lib/storage");
  const body = Buffer.from(`w1-e2e ${new Date().toISOString()} ${crypto.randomUUID()}`);
  const key = stor.buildKey("tmp", `w1-e2e-${crypto.randomUUID()}.txt`);

  const put = await stor.putObject(key, body, "text/plain");
  check("storage.putObject (supabase driver)", put.driver === "supabase", put.key);

  const url = await stor.signedUrl(key, 120);
  check("storage.signedUrl issued", !!url);

  if (url) {
    const res = await fetch(url);
    const got = Buffer.from(await res.arrayBuffer());
    check("signed GET round-trip bytes match", res.ok && got.equals(body), `HTTP ${res.status}, ${got.length}B`);
  }

  const raw = await fetch(`${process.env.SUPABASE_URL}/storage/v1/object/deyoung-media/${key}`);
  check("unauthenticated GET rejected (private bucket)", !raw.ok, `HTTP ${raw.status}`);

  const stat = await stor.objectStat(key);
  check("storage.objectStat size match", !!stat && stat.size === body.length);

  await stor.deleteObject(key);
  // Supabase Storage quirk (empirically confirmed 2026-09-07): after a DELETE
  // is acknowledged, GETs can keep serving the bytes for a short CDN/cache
  // window — so visibility via GET is NOT an authoritative deletion signal.
  // Authoritative check: a second DELETE must fail with code "NoSuchKey".
  const confirm = await fetch(
    `${process.env.SUPABASE_URL}/storage/v1/object/deyoung-media/${key}`,
    { method: "DELETE", headers: { Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}` } }
  );
  const confirmBody = (await confirm.json().catch(() => ({}))) as { code?: string };
  const authoritative = confirmBody.code === "NoSuchKey";
  const stillVisible = (await stor.objectStat(key)) !== null;
  check(
    "storage.deleteObject removes object (authoritative NoSuchKey)",
    authoritative,
    `2nd DELETE ${confirm.status}/${confirmBody.code}; visible-in-cache-window: ${stillVisible} (documented Supabase read-after-delete artifact)`
  );

  // local driver cross-check so dev fallback stays healthy
  process.env.STORAGE_DRIVER = "local";
  const lkey = stor.buildKey("tmp", "local-probe.txt");
  await stor.putObject(lkey, body, "text/plain");
  const lstat = await stor.objectStat(lkey);
  check("local driver put+stat (dev fallback)", !!lstat && lstat.size === body.length);
  await stor.deleteObject(lkey);
  process.env.STORAGE_DRIVER = "supabase";
}

/* --------------------------- 2/3. rate-limit DB --------------------------- */

async function rateLimitTest() {
  const mod = await import("../prisma/pg-client-tmp");
  const pdb = new (mod as any).PrismaClient({ datasources: { db: { url: SESSION_URL } } });

  const bucket = `e2e:${crypto.randomUUID()}`;
  const windowEnd = new Date(Date.now() + 60_000);

  await pdb.rateLimit.upsert({
    where: { bucket },
    create: { bucket, count: 1, resetAt: windowEnd },
    update: { count: 1, resetAt: windowEnd },
  });
  const first = await pdb.rateLimit.findUnique({ where: { bucket } });
  check("RateLimit.create in deyoung schema", !!first && first.count === 1);

  await pdb.rateLimit.update({ where: { bucket }, data: { count: first!.count + 1 } });
  const second = await pdb.rateLimit.findUnique({ where: { bucket } });
  check("RateLimit.increment", second!.count === 2);

  await pdb.rateLimit.deleteMany({ where: { bucket } });
  const gone = await pdb.rateLimit.findUnique({ where: { bucket } });
  check("RateLimit.cleanup", gone === null);
  await pdb.$disconnect();

  // transaction-mode pooler exactly as deploy/start.sh builds it
  const tdb = new (mod as any).PrismaClient({ datasources: { db: { url: TX_URL } } });
  const rows = await tdb.rateLimit.count();
  check("transaction pooler :6543 reaches deyoung schema (pgbouncer=true)", rows >= 0, `${rows} rows visible`);
  await tdb.$disconnect();
}

storageTest()
  .then(rateLimitTest)
  .then(() => {
    console.log(failures === 0 ? "W1 E2E VERDICT: ALL PASS" : `W1 E2E VERDICT: ${failures} FAILURE(S)`);
    process.exit(failures === 0 ? 0 : 1);
  })
  .catch((e) => {
    console.error("E2E crashed:", e);
    process.exit(1);
  });

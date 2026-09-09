#!/usr/bin/env node
/* Task 47 — rotate the owner admin password everywhere (URGENT: it printed
 * into a public GitHub Actions log; rotation was already due anyway).
 * 1. generate a strong password
 * 2. hash with the app's scrypt scheme
 * 3. UPDATE both prod Admin rows
 * 4. update workers/secrets/supabase.json + .env.local (vault sources)
 * Prints the new password ONCE on stdout (owner-only channel). */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt$${salt}$${hash}`;
}

const pw =
  crypto.randomBytes(18).toString("base64url").replace(/[-_]/g, "").slice(0, 20) +
  "!" + crypto.randomBytes(2).toString("hex");
const h = hashPassword(pw);

fs.writeFileSync("/tmp/newadminpw.txt", pw, { mode: 0o600 });

// update vault json + .env.local
const vaultPath = "workers/secrets/supabase.json";
const vault = JSON.parse(fs.readFileSync(vaultPath, "utf8"));
vault.admin_bootstrap = vault.admin_bootstrap || {};
vault.admin_bootstrap.password = pw;
vault.admin_bootstrap.rotated = new Date().toISOString();
vault.admin_bootstrap.rotation_reason = "exposed in public GHA log during Task 47 selftest; rotated immediately";
fs.writeFileSync(vaultPath, JSON.stringify(vault, null, 2));

const envPath = ".env.local";
let env = fs.readFileSync(envPath, "utf8");
env = env.replace(/ADMIN_BOOTSTRAP_PASSWORD=.*/g, "ADMIN_BOOTSTRAP_PASSWORD=" + pw);
fs.writeFileSync(envPath, env);

console.log("NEW ADMIN PASSWORD: " + pw);
console.log("hash updated in " + vaultPath + " and .env.local — DB update next");
console.log("SCRYPT_HASH_FOR_DB: " + h);

/* --- atomic DB update (single-run consistency) --- */
(async () => {
  const { execSync } = require("child_process");
  const out = execSync(
    `/home/z/.venv/bin/python -c "
import json, psycopg2
h='${h}'
vault=json.load(open('workers/secrets/supabase.json')); url=vault['railway_env']['DATABASE_URL'].split('?')[0]+'?sslmode=require'
conn=psycopg2.connect(url); cur=conn.cursor()
cur.execute('UPDATE deyoung.\\"Admin\\" SET \\"passwordHash\\"=%s', (h,))
print('DB rows updated:', cur.rowcount)
conn.commit(); conn.close()
"`
  ).toString();
  console.log(out.trim());
})();

#!/usr/bin/env python3
"""Task 47 — verify the rotated admin password: vault <-> .env.local <-> prod DB.
Reimplements the app's scrypt scheme exactly (hashPassword in src/lib/auth.ts)."""
import hashlib
import json

import psycopg2

vault = json.load(open("/home/z/my-project/workers/secrets/supabase.json"))
pw = vault["admin_bootstrap"]["password"]

env = {}
for line in open("/home/z/my-project/.env.local"):
    if line.startswith("ADMIN_BOOTSTRAP_PASSWORD="):
        env["pw"] = line.strip().split("=", 1)[1]

url = vault["railway_env"]["DATABASE_URL"].split("?")[0] + "?sslmode=require"
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute('SELECT email, "passwordHash" FROM deyoung."Admin"')
rows = cur.fetchall()
conn.close()

print("vault pw set:", bool(pw), "| env pw matches vault:", env.get("pw") == pw)

ok_all = env.get("pw") == pw
for email, stored in rows:
    scheme, salt, digest = stored.split("$")
    cand = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=64)
    ok = scheme == "scrypt" and cand.hex() == digest
    print(f"DB row {email}: password verifies -> {ok}")
    ok_all = ok_all and ok

# scryptSync defaults: N=16384, r=8, p=1, keylen=64 — match Python params above
print("VERDICT:", "CONSISTENT" if ok_all else "INCONSISTENT")

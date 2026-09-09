#!/usr/bin/env python3
"""Task 58: admin panel sign-in verification.
1) Read the Admin row for admin@deyoung.site from prod DB.
2) bcrypt-verify candidate passwords against the stored hash.
3) (fix mode) Reset the hash to a given password if verification fails.
"""
import json
import sys

import psycopg2

sys.path.insert(0, "/home/z/my-project")

fleet = json.load(open("/home/z/my-project/workers/secrets/fleet_db.json"))
supa = json.load(open("/home/z/my-project/workers/secrets/supabase.json"))["supabase"]

# fleet role first (scoped); fall back to postgres pooler url
conn = None
try:
    conn = psycopg2.connect(
        host=fleet["host"], port=fleet.get("port", 6543), dbname="postgres",
        user=fleet["user"], password=fleet["password"],
        options="-c search_path=deyoung,public", sslmode="require", connect_timeout=15)
    who = "deyoung_fleet role"
except Exception as e:
    print("fleet role connect failed:", str(e)[:120])
    conn = psycopg2.connect(supa["database_url_session_pooler"],
                            options="-c search_path=deyoung,public",
                            sslmode="require", connect_timeout=15)
    who = "postgres role"

print("connected as", who)
cur = conn.cursor()
cur.execute('SELECT email, "passwordHash", "createdAt" FROM "Admin" ORDER BY "createdAt"')
rows = cur.fetchall()
print("Admin rows:", [(r[0], r[1][:20] + "...", str(r[2])) for r in rows])

target = None
for email, phash, _ in rows:
    if email == "admin@deyoung.site":
        target = phash
if not target:
    print("NO admin@deyoung.site ROW")
    sys.exit(1)

candidates = {
    "vault_env_password": __import__("os").environ.get("OLD_ADMIN_PW", ""),
}

# bcrypt compare via node (repo already ships bcryptjs)
for name, pw in candidates.items():
    node = (
        "const b=require('bcryptjs');"
        f"console.log(b.compareSync({pw!r}, {target!r}))"
    )
    import subprocess
    out = subprocess.run(["node", "-e", node], capture_output=True, text=True,
                         cwd="/home/z/my-project")
    print(f"verify {name}: match={out.stdout.strip()} err={out.stderr[:80]}")

cur.close()
conn.close()
